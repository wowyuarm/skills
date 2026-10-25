#!/usr/bin/env node
// Stub ablation: keep an exported factory's signature but make its body throw,
// so the whole system still compiles and every runtime touchpoint fails loudly.
//
// Usage: node ablate-stub.mjs <repoDir> <srcRelFile> <fnName> <outJson>
//   srcRelFile is relative to src/ (e.g. "agents/orientation.ts"); fnName is an
//   exported function whose body should be replaced by a throw.
// Env:
//   ABLATION_BUILD_CMD  command that produces a runnable build (default "npm run build")
//   ABLATION_TEST_CMD   command that runs the full suite   (default "npm test")
import { execSync, spawnSync } from "node:child_process";
import { mkdirSync, rmSync, symlinkSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";

const [repoDirRaw, srcRelFile, fnName, outJson] = process.argv.slice(2);
const repoDir = path.resolve(repoDirRaw);
const buildCmd = process.env.ABLATION_BUILD_CMD ?? "npm run build";
const testCmd = process.env.ABLATION_TEST_CMD ?? "npm test";
const slug = `stub__${srcRelFile.replaceAll("/", "__")}`;
const worktrees = "/tmp/codebase-ablation";
const wt = path.join(worktrees, slug);

const fail = (stage, error) => {
  console.error(`[${slug}] failed at ${stage}: ${String(error).slice(0, 500)}`);
  cleanup();
  process.exit(1);
};

function cleanup() {
  try {
    execSync(`git worktree remove --force "${wt}"`, { cwd: repoDir, stdio: "ignore" });
  } catch {}
  try {
    execSync("git worktree prune", { cwd: repoDir, stdio: "ignore" });
  } catch {}
}

try {
  rmSync(wt, { recursive: true, force: true });
  mkdirSync(worktrees, { recursive: true });
  execSync("git worktree prune", { cwd: repoDir, stdio: "ignore" });
  try {
    execSync(`git worktree add --detach "${wt}" HEAD`, { cwd: repoDir, stdio: "ignore" });
  } catch {
    execSync("git worktree prune", { cwd: repoDir, stdio: "ignore" });
    execSync(`git worktree add --detach "${wt}" HEAD`, { cwd: repoDir, stdio: "ignore" });
  }
  if (!existsSync(wt)) throw new Error(`worktree missing after add: ${wt}`);
  const nm = path.join(repoDir, "node_modules");
  if (existsSync(nm)) symlinkSync(nm, path.join(wt, "node_modules"));

  // 1. Insert a throw at the very start of the factory body.
  const file = path.join(wt, "src", srcRelFile);
  const text = readFileSync(file, "utf8");
  const sig = new RegExp(`export\\s+(?:async\\s+)?function\\s+${fnName}\\b`);
  const m = text.match(sig);
  if (!m) fail("edit", `export function ${fnName} not found in ${srcRelFile}`);
  let i = m.index + m[0].length;
  while (text[i] !== "(" && i < text.length) i += 1;
  let depth = 0;
  for (; i < text.length; i += 1) {
    if (text[i] === "(") depth += 1;
    else if (text[i] === ")") {
      depth -= 1;
      if (depth === 0) break;
    }
  }
  while (i < text.length && text[i] !== "{") i += 1;
  const marker = `[ablated] ${fnName} disabled by codebase-ablation`;
  const patched =
    text.slice(0, i + 1) + `\n  throw new Error(${JSON.stringify(marker)});` + text.slice(i + 1);
  writeFileSync(file, patched);

  // 2. Build via the project's own entrypoint.
  const build = spawnSync(buildCmd, { cwd: wt, shell: true, encoding: "utf8", timeout: 600_000 });
  if (build.status !== 0 || build.error) {
    fail("build", (build.error ? String(build.error) : "") + (build.stderr ?? "") + (build.stdout ?? ""));
  }

  // 3. Sanity: the throw must exist in compiled output (tsc-mirroring layouts).
  const distFile = path.join(wt, "dist", "src", srcRelFile.replace(/\.ts$/, ".js"));
  if (existsSync(distFile)) {
    if (!readFileSync(distFile, "utf8").includes(marker)) {
      fail("sanity", `marker missing from ${distFile}`);
    }
  }

  // 4. Run the full suite via the project's own entrypoint.
  const run = spawnSync(testCmd, { cwd: wt, shell: true, encoding: "utf8", timeout: 1_800_000 });
  const out = (run.stdout ?? "") + (run.stderr ?? "");
  let tests = 0,
    pass = 0,
    failCount = 0;
  for (const mm of out.matchAll(/ℹ (tests|pass|fail)\s+(\d+)/g)) {
    if (mm[1] === "tests") tests = Number(mm[2]);
    if (mm[1] === "pass") pass = Number(mm[2]);
    if (mm[1] === "fail") failCount = Number(mm[2]);
  }
  const failures = [];
  let failureDetails = "";
  const failIdx = out.indexOf("✖ failing tests:");
  if (failIdx >= 0) {
    failureDetails = out.slice(failIdx, failIdx + 6000);
    let inFailures = false;
    for (const line of out.split("\n")) {
      if (line.startsWith("✖ failing tests:")) {
        inFailures = true;
        continue;
      }
      if (inFailures && line.startsWith("✖ ")) {
        failures.push(line.replace(/^✖\s+/, "").replace(/\s+\(\d+(\.\d+)?m?s\)$/, ""));
      }
    }
  }

  const result = {
    target: srcRelFile,
    function: fnName,
    mode: "stub",
    tests,
    pass,
    fail: failCount,
    testExitCode: run.status,
    failures,
    rawTail: out.slice(-2000),
    failureDetails,
  };
  mkdirSync(path.dirname(outJson), { recursive: true });
  writeFileSync(outJson, JSON.stringify(result, null, 2));
  console.log(`[${slug}] ${tests} tests ran, ${failCount} failed`);
} catch (error) {
  fail("setup/run", error);
} finally {
  cleanup();
}
