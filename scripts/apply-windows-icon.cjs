const path = require("path");
const rcedit = require("rcedit");

module.exports = async function applyWindowsIcon(context) {
  if (context.electronPlatformName !== "win32") {
    return;
  }

  const iconPath = path.join(context.packager.projectDir, "build", "icons", "icon.ico");
  const exePath = path.join(
    context.appOutDir,
    `${context.packager.appInfo.productFilename}.exe`,
  );

  await rcedit(exePath, {
    icon: iconPath,
    "requested-execution-level": "asInvoker",
  });
};
