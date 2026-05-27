#!/usr/bin/env node
// Tiny launcher: exec `python -m studio.mcp`. Friendly error if studio isn't
// installed. Designed to be referenced from Claude Desktop's
// `claude_desktop_config.json` as:
//
//   {
//     "mcpServers": {
//       "studio": { "command": "npx", "args": ["-y", "@monksudo/studio-mcp"] }
//     }
//   }

const { spawn } = require("node:child_process");

const PY = process.env.STUDIO_PYTHON || "python3";

const child = spawn(PY, ["-m", "studio.mcp"], {
  stdio: "inherit",
  env: process.env,
});

child.on("error", (err) => {
  if (err.code === "ENOENT") {
    process.stderr.write(
      "studio-mcp: could not find python3. Set STUDIO_PYTHON or install Python 3.10+.\n"
    );
    process.exit(127);
  }
  process.stderr.write(`studio-mcp: ${err.message}\n`);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) process.exit(0);
  process.exit(code == null ? 0 : code);
});
