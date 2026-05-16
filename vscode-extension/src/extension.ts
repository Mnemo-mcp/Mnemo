import * as vscode from "vscode";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { createWriteStream, chmodSync, existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import * as path from "node:path";
import * as https from "node:https";
import * as os from "node:os";

const execFileAsync = promisify(execFile);

const REPO = "nikhil1057/Mnemo";
const BINARY_NAME = os.platform() === "win32" ? "mnemo.exe" : "mnemo";

function getPlatformArtifact(): string {
  const platform = os.platform();
  if (platform === "darwin") {
    return "mnemo-darwin-arm64";
  }
  if (platform === "linux") {
    return "mnemo-linux-x64";
  }
  return "mnemo-win-x64.exe";
}

function binDir(context: vscode.ExtensionContext): string {
  return path.join(context.globalStorageUri.fsPath, "bin");
}

function binaryPath(context: vscode.ExtensionContext): string {
  return path.join(binDir(context), BINARY_NAME);
}

async function downloadFile(url: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const follow = (u: string) => {
      https.get(u, (res) => {
        if (res.statusCode === 302 || res.statusCode === 301) {
          follow(res.headers.location!);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`Download failed: HTTP ${res.statusCode}`));
          return;
        }
        const file = createWriteStream(dest);
        res.pipe(file);
        file.on("finish", () => { file.close(); resolve(); });
      }).on("error", reject);
    };
    follow(url);
  });
}

async function getLatestVersion(): Promise<string> {
  return new Promise((resolve, reject) => {
    https.get(
      `https://api.github.com/repos/${REPO}/releases/latest`,
      { headers: { "User-Agent": "mnemo-vscode" } },
      (res) => {
        let data = "";
        res.on("data", (chunk) => { data += chunk; });
        res.on("end", () => {
          try {
            resolve(JSON.parse(data).tag_name ?? "v0.1.0");
          } catch {
            reject(new Error("Failed to parse release info"));
          }
        });
      }
    ).on("error", reject);
  });
}

async function ensureBinary(context: vscode.ExtensionContext): Promise<string> {
  const bin = binaryPath(context);
  if (existsSync(bin)) {
    return bin;
  }

  // Try downloading binary from GitHub Releases (no Python needed)
  try {
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Mnemo: Downloading..." },
      async () => {
        const dir = binDir(context);
        await mkdir(dir, { recursive: true });
        const version = await getLatestVersion();
        const artifact = getPlatformArtifact();
        const url = `https://github.com/${REPO}/releases/download/${version}/${artifact}`;
        await downloadFile(url, bin);
        if (os.platform() !== "win32") {
          chmodSync(bin, 0o755);
        }
      }
    );
    return bin;
  } catch { /* binary not available yet, try PATH fallbacks */ }

  // Check if mnemo is on PATH (pip install or manual)
  try {
    const { stdout } = await execFileAsync("mnemo", ["--help"]);
    if (stdout.includes("Usage")) {
      return "mnemo";
    }
  } catch { /* not on PATH */ }

  // Check common pip install locations as last resort
  const pipPaths = [
    path.join(os.homedir(), "Library", "Python", "3.12", "bin", "mnemo"),
    path.join(os.homedir(), "Library", "Python", "3.11", "bin", "mnemo"),
    path.join(os.homedir(), ".local", "bin", "mnemo"),
  ];
  for (const p of pipPaths) {
    if (existsSync(p)) {
      return p;
    }
  }

  throw new Error("Mnemo not available. Binary download failed and mnemo not found on PATH. Install with: pip install mnemo");
}

async function runMnemo(context: vscode.ExtensionContext, args: string[], cwd: string): Promise<string> {
  const bin = await ensureBinary(context);
  const { stdout, stderr } = await execFileAsync(bin, args, { cwd });
  return `${stdout}\n${stderr}`.trim();
}

function workspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

export function activate(context: vscode.ExtensionContext): void {
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 50);
  statusBar.command = "mnemo.showStatus";
  statusBar.text = "$(database) Mnemo";
  context.subscriptions.push(statusBar);

  // Auto-init on workspace open
  const root = workspaceRoot();
  if (root) {
    const mnemoDir = path.join(root, ".mnemo");
    if (existsSync(mnemoDir)) {
      statusBar.text = "$(database) Mnemo: Active";
      statusBar.show();
    } else {
      // Prompt user once
      vscode.window
        .showInformationMessage("Mnemo: Initialize project memory for this workspace?", "Yes", "Not now")
        .then(async (choice) => {
          if (choice === "Yes") {
            try {
              // Detect which clients are available and only configure those
              const clients: string[] = [];
              const amazonqExt = vscode.extensions.getExtension("amazonwebservices.amazon-q-vscode");
              const cursorConfig = path.join(os.homedir(), ".cursor");
              const claudeConfig = path.join(os.homedir(), ".claude");
              const kiroConfig = path.join(root, ".kiro");
              
              if (amazonqExt) { clients.push("amazonq"); }
              if (existsSync(cursorConfig)) { clients.push("cursor"); }
              if (existsSync(claudeConfig)) { clients.push("claude-code"); }
              if (existsSync(kiroConfig)) { clients.push("kiro"); }
              
              let clientArg: string;
              if (clients.length > 1) {
                clientArg = "all";
              } else if (clients.length === 1) {
                clientArg = clients[0];
              } else {
                // No client detected — ask the user
                const pick = await vscode.window.showQuickPick(
                  ["amazonq", "cursor", "claude-code", "kiro", "copilot", "generic", "all"],
                  { placeHolder: "Which AI client do you use?" }
                );
                if (!pick) { return; }
                clientArg = pick;
              }
              await runMnemo(context, ["init", "--client", clientArg], root);
              statusBar.text = "$(database) Mnemo: Active";
              statusBar.show();
              vscode.window.showInformationMessage("Mnemo initialized.");
            } catch (e) {
              vscode.window.showErrorMessage(`Mnemo init failed: ${String(e)}`);
            }
          }
        });
    }
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("mnemo.initWorkspace", async () => {
      const cwd = workspaceRoot();
      if (!cwd) { vscode.window.showWarningMessage("Open a workspace folder first."); return; }
      try {
        // Detect which clients are available
        const clients: string[] = [];
        const amazonqExt = vscode.extensions.getExtension("amazonwebservices.amazon-q-vscode");
        const cursorConfig = path.join(os.homedir(), ".cursor");
        const claudeConfig = path.join(os.homedir(), ".claude");
        const kiroConfig = path.join(cwd, ".kiro");
        
        if (amazonqExt) { clients.push("amazonq"); }
        if (existsSync(cursorConfig)) { clients.push("cursor"); }
        if (existsSync(claudeConfig)) { clients.push("claude-code"); }
        if (existsSync(kiroConfig)) { clients.push("kiro"); }
        
        let clientArg: string;
        if (clients.length > 1) {
          clientArg = "all";
        } else if (clients.length === 1) {
          clientArg = clients[0];
        } else {
          const pick = await vscode.window.showQuickPick(
            ["amazonq", "cursor", "claude-code", "kiro", "copilot", "generic", "all"],
            { placeHolder: "Which AI client do you use?" }
          );
          if (!pick) { return; }
          clientArg = pick;
        }
        const out = await runMnemo(context, ["init", "--client", clientArg], cwd);
        statusBar.text = "$(database) Mnemo: Active";
        statusBar.show();
        vscode.window.showInformationMessage(out || "Mnemo initialized.");
      } catch (e) {
        vscode.window.showErrorMessage(`Mnemo init failed: ${String(e)}`);
      }
    }),

    vscode.commands.registerCommand("mnemo.showStatus", async () => {
      const cwd = workspaceRoot();
      if (!cwd) { vscode.window.showWarningMessage("Open a workspace folder first."); return; }
      try {
        const out = await runMnemo(context, ["doctor"], cwd);
        const doc = await vscode.workspace.openTextDocument({ content: out, language: "markdown" });
        await vscode.window.showTextDocument(doc, { preview: false });
      } catch (e) {
        vscode.window.showErrorMessage(`Mnemo doctor failed: ${String(e)}`);
      }
    }),

    vscode.commands.registerCommand("mnemo.refreshIndex", async () => {
      const cwd = workspaceRoot();
      if (!cwd) { vscode.window.showWarningMessage("Open a workspace folder first."); return; }
      try {
        statusBar.text = "$(sync~spin) Mnemo: Indexing...";
        const out = await runMnemo(context, ["map"], cwd);
        statusBar.text = "$(database) Mnemo: Active";
        vscode.window.showInformationMessage(out || "Index refreshed.");
      } catch (e) {
        statusBar.text = "$(database) Mnemo: Active";
        vscode.window.showErrorMessage(`Mnemo map failed: ${String(e)}`);
      }
    }),

    vscode.commands.registerCommand("mnemo.resetWorkspace", async () => {
      const cwd = workspaceRoot();
      if (!cwd) { vscode.window.showWarningMessage("Open a workspace folder first."); return; }
      const confirm = await vscode.window.showWarningMessage(
        "This will delete all Mnemo memory for this workspace. Are you sure?",
        { modal: true },
        "Reset"
      );
      if (confirm !== "Reset") { return; }
      try {
        const out = await runMnemo(context, ["reset", "--yes"], cwd);
        statusBar.text = "$(database) Mnemo";
        vscode.window.showInformationMessage(out || "Mnemo reset complete. Run Initialize to start fresh.");
      } catch (e) {
        vscode.window.showErrorMessage(`Mnemo reset failed: ${String(e)}`);
      }
    }),

    vscode.commands.registerCommand("mnemo.detectInstall", async () => {
      try {
        const bin = await ensureBinary(context);
        vscode.window.showInformationMessage(`Mnemo ready: ${bin}`);
      } catch (e) {
        vscode.window.showErrorMessage(`Mnemo not available: ${String(e)}`);
      }
    })
  );
}

export function deactivate(): void {}
