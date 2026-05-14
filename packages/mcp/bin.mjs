#!/usr/bin/env node
import { spawn } from "child_process";

const child = spawn("mnemo", ["mcp-server"], { stdio: "inherit" });

child.on("error", (err) => {
  if (err.code === "ENOENT") {
    process.stderr.write(
      "Error: 'mnemo' not found on PATH.\n" +
      "Install it first: pip install mnemo-dev\n" +
      "Or: brew install mnemo\n"
    );
  } else {
    process.stderr.write(`Error spawning mnemo: ${err.message}\n`);
  }
  process.exit(1);
});

child.on("exit", (code) => process.exit(code ?? 1));
