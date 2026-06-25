import os
import urllib.request
import zipfile
import shutil
from pathlib import Path

# --- DEPENDENCY SETUP ---
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

# --- FULL C++ ORCHESTRATOR CODE ---
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

namespace fs = std::filesystem;

struct TargetProject {
    std::string folderPath;
    std::string detectedFile;
    int port = 5000;
    char subdomainInput[64] = "my-app-test";
    bool isRunning = false;
    std::string tunnelUrl = "Offline";
};

std::vector<TargetProject> projects;
const std::string CONFIG_FILE = "config.txt";

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
    
    // Prevent duplicate folder mounts
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

int main() {
    if (!glfwInit()) return 1;
    glfwWindowHint(GLFW_RESIZABLE, GLFW_FALSE);
    GLFWwindow* window = glfwCreateWindow(850, 500, "HOST", NULL, NULL);
    glfwMakeContextCurrent(window);
    
    ImGui::CreateContext();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");

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

        int id_counter = 0;
        for (auto& proj : projects) {
            // Push a unique numerical ID onto the stack for this UI grouping loop
            ImGui::PushID(id_counter++);
            
            ImGui::Separator();
            ImGui::Text("File: %s", proj.detectedFile.c_str());
            ImGui::Text("Auto-Detected Port: %d", proj.port);
            ImGui::InputText("Subdomain", proj.subdomainInput, 64);
            
            if (ImGui::Button(proj.isRunning ? "Kill Server" : "Boot Tunnel")) {
                if (!proj.isRunning) {
                    std::string serverCmd = "C:\\Windows\\System32\\cmd.exe /c start \"HOST Python Server\" cmd /k \"cd /d " + proj.folderPath + 
                                           " && " + nativePython + " -m pip install flask google-genai & " + nativePython + " " + proj.detectedFile + "\"";
                    std::system(serverCmd.c_str());
                    
                    std::string tunnelCmd = "C:\\Windows\\System32\\cmd.exe /c start \"HOST Tunnel Connection\" cmd /k npx localtunnel --port " + std::to_string(proj.port) + 
                                           " --subdomain " + std::string(proj.subdomainInput) + " ^> lt.log 2^>^&1";
                    std::system(tunnelCmd.c_str());
                    
                    proj.isRunning = true;
                } else {
                    std::system("C:\\Windows\\System32\\taskkill.exe /F /IM node.exe /T");
                    std::system("C:\\Windows\\System32\\taskkill.exe /F /IM python.exe /T");
                    proj.isRunning = false;
                    proj.tunnelUrl = "Offline";
                }
            }
            ImGui::SameLine();
            if (ImGui::Button("Sync Link")) {
                std::ifstream log("lt.log");
                if (log.is_open()) {
                    std::string line;
                    bool found = false;
                    while(std::getline(log, line)) {
                        if (line.find("url is") != std::string::npos) {
                            proj.tunnelUrl = line;
                            found = true;
                        }
                    }
                    if(!found) {
                        proj.tunnelUrl = "Loading or Waiting for Output...";
                    }
                }
            }
            ImGui::TextWrapped("Status: %s", proj.tunnelUrl.c_str());
            
            // Pop the unique ID off the stack so the next project gets its own isolated identifier
            ImGui::PopID();
        }
        ImGui::End();
        
        ImGui::Render();
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(window);
    }
    return 0;
}
"""

def compile_and_run():
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
