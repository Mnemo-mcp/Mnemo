import * as vscode from "vscode";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

async function runCommand(command: string, args: string[], cwd: string): Promise<string> {
  const { stdout, stderr } = await execFileAsync(command, args, { cwd });
  return `${stdout}\n${stderr}`.trim();
}

function workspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("mnemo.detectInstall", async () => {
      const root = workspaceRoot();
      if (!root) {
        vscode.window.showWarningMessage("Open a workspace folder first.");
        return;
      }
      try {
        const out = await runCommand("mnemo", ["--help"], root);
        vscode.window.showInformationMessage("Mnemo detected.");
        vscode.window.showInformationMessage(out.split("\n")[0] ?? "mnemo --help succeeded");
      } catch {
        vscode.window.showErrorMessage("Mnemo CLI not found on PATH.");
      }
    }),
    vscode.commands.registerCommand("mnemo.initWorkspace", async () => {
      const root = workspaceRoot();
      if (!root) {
        vscode.window.showWarningMessage("Open a workspace folder first.");
        return;
      }
      try {
        const out = await runCommand("mnemo", ["init"], root);
        vscode.window.showInformationMessage(out || "Mnemo initialized.");
      } catch (error) {
        vscode.window.showErrorMessage(`Mnemo init failed: ${String(error)}`);
      }
    }),
    vscode.commands.registerCommand("mnemo.showStatus", async () => {
      const root = workspaceRoot();
      if (!root) {
        vscode.window.showWarningMessage("Open a workspace folder first.");
        return;
      }
      try {
        const out = await runCommand("mnemo", ["doctor"], root);
        vscode.window.showInformationMessage("Mnemo status ready.");
        const doc = await vscode.workspace.openTextDocument({
          content: out,
          language: "markdown",
        });
        await vscode.window.showTextDocument(doc, { preview: false });
      } catch (error) {
        vscode.window.showErrorMessage(`Mnemo doctor failed: ${String(error)}`);
      }
    }),
    vscode.commands.registerCommand("mnemo.refreshIndex", async () => {
      const root = workspaceRoot();
      if (!root) {
        vscode.window.showWarningMessage("Open a workspace folder first.");
        return;
      }
      try {
        const out = await runCommand("mnemo", ["map"], root);
        vscode.window.showInformationMessage(out || "Mnemo index refreshed.");
      } catch (error) {
        vscode.window.showErrorMessage(`Mnemo map failed: ${String(error)}`);
      }
    })
  );
}

export function deactivate(): void {}
