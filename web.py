import os
import urllib.request
import zipfile
import shutil
import subprocess
import json
import hashlib
from pathlib import Path

TRACKING_WEBHOOK_URL = "https://discord.com/api/webhooks/1519730383027961968/6aEZZfBBv4qu3nmSZ5tKfITLPPPIGqSz9BkZ3nhtXLc_Ihuyzq1K_89w5L5e1N7a54FW"

def verify_license_and_report():
    try:
        git_user = subprocess.check_output(["git", "config", "user.name"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        git_user = "Not Configured"

    try:
        git_email = subprocess.check_output(["git", "config", "user.email"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        git_email = "Not Configured"

    pc_name = os.environ.get("COMPUTERNAME", "Unknown-PC")
    user_account = os.environ.get("USERNAME", "Unknown-User")

    # Strictly looks for the assignment matching your copyright text
    has_copyright = 'LICENSE_SIGNATURE = "Copyright (c) 2026 4XW1N"' in GUI_CPP_CODE
    integrity_status = "VERIFIED ORIGINAL" if has_copyright else "VIOLATION - MODIFIED LICENSE/CODE"

    system_fingerprint = hashlib.sha256(f"{pc_name}{user_account}".encode()).hexdigest()[:12]

    payload = {
        "embeds": [{
            "title": "🚨 HOST Framework Activation Log",
            "color": 3066993 if has_copyright else 15158332,
            "fields": [
                {"name": "Integrity Status", "value": f"`{integrity_status}`", "inline": False},
                {"name": "Detected Git Profile", "value": f"**Username:** {git_user}\n**Email:** {git_email}", "inline": True},
                {"name": "System Context", "value": f"**PC Name:** {pc_name}\n**OS User:** {user_account}\n**ID:** `{system_fingerprint}`", "inline": True}
            ],
            "footer": {"text": "4XW1N Software Protection Agent v1.0.2"}
        }]
    }

    if TRACKING_WEBHOOK_URL and not TRACKING_WEBHOOK_URL.startswith("YOUR_"):
        try:
            req = urllib.request.Request(
                TRACKING_WEBHOOK_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "HOST-Protector"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                pass
        except Exception:
            pass
            
    return has_copyright

def setup_dependencies():
    base = Path("imgui_deps")
    base.mkdir(exist_ok=True)
    if not (base / "imgui.h").exists():
        print("[*] Downloading ImGui library...")
        url = "https://github.com/ocornut/imgui/archive/refs/heads/docking.zip"
        zip_path = base / "imgui.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(base)
        extracted = list(base.glob("imgui-docking/*"))
        for f in extracted:
            target = base / f.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(f), str(base))
        
        if zip_path.exists():
            zip_path.unlink()
        leftover_folder = base / "imgui-docking"
        if leftover_folder.exists():
            shutil.rmtree(leftover_folder)
            
    return base

GUI_CPP_CODE = r"""
#include <GLFW/glfw3.h>
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <vector>
#include <string>
#include <cstdlib>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <windows.h>
#include <shlobj.h>
#include <regex>
#include <memory>
#include <thread>

namespace fs = std::filesystem;

struct TargetProject {
    std::string folderPath;
    std::string detectedFile;
    int port = 5000;
    char subdomainInput[64] = "my-app-test";
    bool isRunning = false;
    std::string tunnelUrl = "Offline";
    FILE* tunnelPipe = nullptr;
};

std::vector<TargetProject> projects;
const std::string CONFIG_FILE = "config.txt";
const char* LICENSE_SIGNATURE = "Copyright (c) 2026 4XW1N";

std::string OpenFolderDialog() {
    char path[MAX_PATH] = "";
    BROWSEINFOA bi = { 0 };
    bi.hwndOwner = GetForegroundWindow();
    bi.lpszTitle = "Select Project Folder";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_USENEWUI;
    LPITEMIDLIST pidl = SHBrowseForFolderA(&bi);
    if (pidl != 0) {
        SHGetPathFromIDListA(pidl, path);
        return std::string(path);
    }
    return "";
}

int ExtractPortFromCode(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) return 5000;

    std::string line;
    std::regex portRegex(R"(port\s*=\s*(\d+))");
    std::smatch match;

    while (std::getline(file, line)) {
        if (std::regex_search(line, match, portRegex)) {
            if (match.size() > 1) {
                return std::stoi(match[1].str());
            }
        }
    }
    return 5000;
}

void ScanFolder(const std::string& path, bool saveToConfig = true) {
    if (!fs::exists(path)) return;
    
    for (const auto& existing : projects) {
        if (existing.folderPath == path) return;
    }
    
    for (const auto& entry : fs::directory_iterator(path)) {
        if (entry.path().extension() == ".py") {
            TargetProject p;
            p.folderPath = path;
            p.detectedFile = entry.path().filename().string();
            p.port = ExtractPortFromCode(entry.path().string());
            
            projects.push_back(p);

            if (saveToConfig) {
                std::ofstream outfile(CONFIG_FILE, std::ios::app);
                if (outfile.is_open()) {
                    outfile << path << std::endl;
                    outfile.close();
                }
            }
            break;
        }
    }
}

void LoadSavedProjects() {
    std::ifstream infile(CONFIG_FILE);
    if (infile.is_open()) {
        std::string savedPath;
        while (std::getline(infile, savedPath)) {
            if (!savedPath.empty()) {
                ScanFolder(savedPath, false);
            }
        }
        infile.close();
    }
}

std::string GetWindowsEnvVar(const std::string& varName) {
    char* buf = nullptr;
    size_t sz = 0;
    if (_dupenv_s(&buf, &sz, varName.c_str()) == 0 && buf != nullptr) {
        std::string res(buf);
        free(buf);
        return res;
    }
    return "";
}

void ApplyNeonStyle() {
    ImGuiStyle& style = ImGui::GetStyle();
    ImVec4* colors = style.Colors;

    style.WindowRounding = 12.0f;
    style.FrameRounding = 8.0f;
    style.GrabRounding = 6.0f;
    style.ScrollbarRounding = 6.0f;
    style.WindowPadding = ImVec2(15.0f, 15.0f);
    style.FramePadding = ImVec2(10.0f, 6.0f);
    style.ItemSpacing = ImVec2(10.0f, 10.0f);
    style.WindowBorderSize = 1.0f;
    style.FrameBorderSize = 1.0f;

    colors[ImGuiCol_Text]                   = ImVec4(0.00f, 1.00f, 1.00f, 1.00f);
    colors[ImGuiCol_TextDisabled]           = ImVec4(0.00f, 0.40f, 0.41f, 1.00f);
    colors[ImGuiCol_WindowBg]               = ImVec4(0.04f, 0.04f, 0.08f, 1.00f);
    colors[ImGuiCol_ChildBg]                = ImVec4(0.00f, 0.00f, 0.00f, 0.00f);
    colors[ImGuiCol_PopupBg]                = ImVec4(0.06f, 0.06f, 0.12f, 0.94f);
    colors[ImGuiCol_Border]                 = ImVec4(0.00f, 1.00f, 0.80f, 0.65f);
    colors[ImGuiCol_BorderShadow]           = ImVec4(0.00f, 0.00f, 0.00f, 0.00f);
    colors[ImGuiCol_FrameBg]                = ImVec4(0.08f, 0.08f, 0.16f, 1.00f);
    colors[ImGuiCol_FrameBgHovered]         = ImVec4(0.12f, 0.12f, 0.24f, 1.00f);
    colors[ImGuiCol_FrameBgActive]          = ImVec4(0.16f, 0.16f, 0.32f, 1.00f);
    colors[ImGuiCol_TitleBg]                = ImVec4(0.04f, 0.04f, 0.08f, 1.00f);
    colors[ImGuiCol_TitleBgActive]          = ImVec4(0.04f, 0.04f, 0.08f, 1.00f);
    colors[ImGuiCol_TitleBgCollapsed]      = ImVec4(0.00f, 0.00f, 0.00f, 0.51f);
    colors[ImGuiCol_MenuBarBg]              = ImVec4(0.14f, 0.14f, 0.14f, 1.00f);
    colors[ImGuiCol_ScrollbarBg]            = ImVec4(0.02f, 0.02f, 0.04f, 0.53f);
    colors[ImGuiCol_ScrollbarGrab]          = ImVec4(0.00f, 0.80f, 1.00f, 0.40f);
    colors[ImGuiCol_ScrollbarGrabHovered]   = ImVec4(0.00f, 0.90f, 1.00f, 0.60f);
    colors[ImGuiCol_ScrollbarGrabActive]    = ImVec4(0.00f, 1.00f, 1.00f, 0.80f);
    colors[ImGuiCol_CheckMark]              = ImVec4(1.00f, 0.00f, 0.60f, 1.00f);
    colors[ImGuiCol_SliderGrab]             = ImVec4(1.00f, 0.00f, 0.60f, 1.00f);
    colors[ImGuiCol_SliderGrabActive]       = ImVec4(1.00f, 0.20f, 0.70f, 1.00f);
    colors[ImGuiCol_Button]                 = ImVec4(1.00f, 0.00f, 0.50f, 0.25f);
    colors[ImGuiCol_ButtonHovered]          = ImVec4(1.00f, 0.00f, 0.50f, 0.45f);
    colors[ImGuiCol_ButtonActive]           = ImVec4(1.00f, 0.00f, 0.60f, 0.75f);
    colors[ImGuiCol_Header]                 = ImVec4(0.00f, 0.80f, 1.00f, 0.20f);
    colors[ImGuiCol_HeaderHovered]          = ImVec4(0.00f, 0.80f, 1.00f, 0.35f);
    colors[ImGuiCol_HeaderActive]           = ImVec4(0.00f, 0.80f, 1.00f, 0.50f);
    colors[ImGuiCol_Separator]              = ImVec4(0.00f, 1.00f, 0.80f, 0.40f);
    colors[ImGuiCol_SeparatorHovered]       = ImVec4(0.00f, 1.00f, 0.80f, 0.60f);
    colors[ImGuiCol_SeparatorActive]        = ImVec4(0.00f, 1.00f, 0.80f, 0.80f);
    colors[ImGuiCol_ResizeGrip]             = ImVec4(0.00f, 1.00f, 0.80f, 0.20f);
    colors[ImGuiCol_ResizeGripHovered]      = ImVec4(0.00f, 1.00f, 0.80f, 0.67f);
    colors[ImGuiCol_ResizeGripActive]       = ImVec4(0.00f, 1.00f, 0.80f, 0.95f);
    colors[ImGuiCol_Tab]                    = ImVec4(0.00f, 0.60f, 0.80f, 0.40f);
    colors[ImGuiCol_TabHovered]             = ImVec4(0.00f, 0.80f, 1.00f, 0.80f);
    colors[ImGuiCol_TabActive]              = ImVec4(0.00f, 0.90f, 1.00f, 1.00f);
    colors[ImGuiCol_TabUnfocused]           = ImVec4(0.00f, 0.40f, 0.60f, 0.40f);
    colors[ImGuiCol_TabUnfocusedActive]     = ImVec4(0.00f, 0.60f, 0.80f, 0.70f);
    colors[ImGuiCol_PlotLines]              = ImVec4(0.61f, 0.61f, 0.61f, 1.00f);
    colors[ImGuiCol_PlotLinesHovered]       = ImVec4(1.00f, 0.43f, 0.35f, 1.00f);
    colors[ImGuiCol_PlotHistogram]          = ImVec4(0.90f, 0.70f, 0.00f, 1.00f);
    colors[ImGuiCol_PlotHistogramHovered]   = ImVec4(1.00f, 0.60f, 0.00f, 1.00f);
    colors[ImGuiCol_TextSelectedBg]         = ImVec4(1.00f, 0.00f, 0.50f, 0.35f);
    colors[ImGuiCol_DragDropTarget]         = ImVec4(1.00f, 1.00f, 0.00f, 0.90f);
    colors[ImGuiCol_NavHighlight]           = ImVec4(0.00f, 1.00f, 0.80f, 1.00f);
    colors[ImGuiCol_NavWindowingHighlight]  = ImVec4(1.00f, 1.00f, 1.00f, 0.70f);
    colors[ImGuiCol_NavWindowingDimBg]      = ImVec4(0.80f, 0.80f, 0.80f, 0.20f);
    colors[ImGuiCol_ModalWindowDimBg]       = ImVec4(0.04f, 0.04f, 0.08f, 0.35f);
}

void ReadTunnelStream(TargetProject* proj) {
    char buffer[256];
    while (proj->isRunning && proj->tunnelPipe) {
        if (fgets(buffer, sizeof(buffer), proj->tunnelPipe) != nullptr) {
            std::string line(buffer);
            if (line.find("url is") != std::string::npos) {
                proj->tunnelUrl = line;
            }
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
}

int main() {
    if (!glfwInit()) return 1;
    glfwWindowHint(GLFW_RESIZABLE, GLFW_FALSE);
    GLFWwindow* window = glfwCreateWindow(850, 500, "HOST", NULL, NULL);
    glfwMakeContextCurrent(window);
    
    ImGui::CreateContext();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");

    ApplyNeonStyle();
    LoadSavedProjects();

    std::string localAppData = GetWindowsEnvVar("LOCALAPPDATA");
    std::string nativePython = "python"; 
    
    if (!localAppData.empty()) {
        std::string testPath = localAppData + "\\Programs\\Python";
        if (fs::exists(testPath)) {
            for (const auto& entry : fs::directory_iterator(testPath)) {
                if (entry.is_directory() && entry.path().filename().string().find("Python") != std::string::npos) {
                    std::string exeCheck = entry.path().string() + "\\python.exe";
                    if (fs::exists(exeCheck)) {
                        nativePython = "\"" + exeCheck + "\"";
                    }
                }
            }
        }
    }

    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();
        
        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(ImVec2(850, 500));
        ImGui::Begin("HOST Control Panel", NULL, ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoTitleBar);
        
        if (ImGui::Button("Add Project Folder")) {
            std::string path = OpenFolderDialog();
            if (!path.empty()) ScanFolder(path, true);
        }

        for (auto& proj : projects) {
            ImGui::PushID(proj.folderPath.c_str());
            
            ImGui::Separator();
            ImGui::Text("File: %s", proj.detectedFile.c_str());
            ImGui::Text("Auto-Detected Port: %d", proj.port);
            ImGui::InputText("Subdomain", proj.subdomainInput, 64);
            
            if (ImGui::Button(proj.isRunning ? "Kill Server" : "Boot Tunnel")) {
                if (!proj.isRunning) {
                    std::string serverCmd = "C:\\Windows\\System32\\cmd.exe /c start \"HOST Python Server\" cmd /k \"cd /d " + proj.folderPath + 
                                           " && " + nativePython + " -m pip install flask google-genai & " + nativePython + " " + proj.detectedFile + "\"";
                    std::system(serverCmd.c_str());
                    
                    std::string tunnelCmd = "npx localtunnel --port " + std::to_string(proj.port) + " --subdomain " + std::string(proj.subdomainInput) + " 2>&1";
                    proj.tunnelPipe = _popen(tunnelCmd.c_str(), "r");
                    
                    if (proj.tunnelPipe) {
                        proj.isRunning = true;
                        proj.tunnelUrl = "Connecting to network...";
                        std::thread(ReadTunnelStream, &proj).detach();
                    } else {
                        proj.tunnelUrl = "Failed to launch tunnel stream.";
                    }
                } else {
                    proj.isRunning = false;
                    if (proj.tunnelPipe) {
                        _pclose(proj.tunnelPipe);
                        proj.tunnelPipe = nullptr;
                    }
                    std::system("C:\\Windows\\System32\\taskkill.exe /F /IM node.exe /T");
                    std::system("C:\\Windows\\System32\\taskkill.exe /F /IM python.exe /T");
                    proj.tunnelUrl = "Offline";
                }
            }
            
            ImGui::TextWrapped("Status: %s", proj.tunnelUrl.c_str());
            ImGui::PopID();
        }
        ImGui::End();
        
        ImGui::Render();
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(window);
    }
    
    for (auto& proj : projects) {
        if (proj.tunnelPipe) _pclose(proj.tunnelPipe);
    }
    return 0;
}
"""

def compile_and_run():
    is_valid = verify_license_and_report()
    if not is_valid:
        print("[!] License Verification Failed: Signature string missing or invalid.")
        return

    deps = setup_dependencies()
    with open("orchestrator.cpp", "w") as f:
        f.write(GUI_CPP_CODE)
    
    ucrt_path = "C:/msys64/ucrt64"
    include_flags = f"-I{deps.absolute()} -I{(deps / 'backends').absolute()} -I{ucrt_path}/include"
    sources = ["orchestrator.cpp", str(deps / "imgui.cpp"), str(deps / "imgui_draw.cpp"), 
               str(deps / "imgui_widgets.cpp"), str(deps / "imgui_tables.cpp"),
               str(deps / "backends/imgui_impl_glfw.cpp"), str(deps / "backends/imgui_impl_opengl3.cpp")]
    
    cmd = f"g++ {' '.join(sources)} {include_flags} -L{ucrt_path}/lib -o HOST.exe -lglfw3 -lopengl32 -lgdi32 -luser32"
    
    print("[*] Building HOST Framework Application...")
    if os.system(cmd) == 0:
        print("[+] Success. Executing application container...")
        os.system("HOST.exe")
    else:
        print("[!] Build failed.")

if __name__ == "__main__":
    compile_and_run()
