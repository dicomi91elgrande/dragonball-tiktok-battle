using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace DragonBallTikTokBattleLauncher
{
    internal static class DragonBallLauncher
    {
        private const string DefaultUrl = "https://dragonball-tiktok-battle.onrender.com/?obs=1&stream=band";
        private const string ConfigFileName = "launcher-config.txt";

        [STAThread]
        private static void Main(string[] args)
        {
            try
            {
                LauncherConfig config = ResolveConfig(args);
                string browser = FindBrowser();

                if (string.IsNullOrWhiteSpace(browser))
                {
                    MessageBox.Show(
                        "No encuentro Edge ni Chrome instalados. Instala uno de los dos y vuelve a abrir el lanzador.",
                        "Dragon Ball TikTok Battle",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                    return;
                }

                string userDataDir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "DragonBallTikTokBattleLauncher");

                Directory.CreateDirectory(userDataDir);

                var startInfo = new ProcessStartInfo
                {
                    FileName = browser,
                    Arguments = BuildBrowserArguments(config, userDataDir),
                    UseShellExecute = false
                };

                Process.Start(startInfo);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    ex.Message,
                    "Dragon Ball TikTok Battle",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        private static LauncherConfig ResolveConfig(string[] args)
        {
            var config = new LauncherConfig
            {
                Url = DefaultUrl,
                Width = 0,
                Height = 0,
                Scale = "1"
            };

            if (args != null && args.Length > 0 && IsHttpUrl(args[0]))
            {
                config.Url = args[0].Trim();
                return config;
            }

            string configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ConfigFileName);
            if (File.Exists(configPath))
            {
                foreach (string rawLine in File.ReadAllLines(configPath))
                {
                    string line = rawLine.Trim();
                    if (line.Length == 0 || line.StartsWith("#"))
                    {
                        continue;
                    }

                    int separator = line.IndexOf('=');
                    if (separator < 0)
                    {
                        if (IsHttpUrl(line))
                        {
                            config.Url = line;
                        }
                        continue;
                    }

                    string key = line.Substring(0, separator).Trim().ToLowerInvariant();
                    string value = line.Substring(separator + 1).Trim();

                    if (key == "url" && IsHttpUrl(value))
                    {
                        config.Url = value;
                    }
                    else if (key == "width")
                    {
                        int.TryParse(value, out config.Width);
                    }
                    else if (key == "height")
                    {
                        int.TryParse(value, out config.Height);
                    }
                    else if (key == "scale" && value.Length > 0)
                    {
                        config.Scale = value.Replace(",", ".");
                    }
                }
            }

            return config;
        }

        private static bool IsHttpUrl(string value)
        {
            Uri uri;
            return Uri.TryCreate(value, UriKind.Absolute, out uri)
                && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
        }

        private static string FindBrowser()
        {
            string[] candidates =
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Google", "Chrome", "Application", "chrome.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Google", "Chrome", "Application", "chrome.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Google", "Chrome", "Application", "chrome.exe")
            };

            return candidates.FirstOrDefault(File.Exists);
        }

        private static string BuildBrowserArguments(LauncherConfig config, string userDataDir)
        {
            string arguments = string.Join(" ", new[]
            {
                "--app=" + Quote(config.Url),
                "--new-window",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=Translate",
                "--user-data-dir=" + Quote(userDataDir)
            });

            if (config.Width > 0 && config.Height > 0)
            {
                arguments += " --window-size=" + config.Width + "," + config.Height;
            }

            if (!string.IsNullOrWhiteSpace(config.Scale))
            {
                arguments += " --force-device-scale-factor=" + config.Scale;
            }

            return arguments;
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private class LauncherConfig
        {
            public string Url;
            public int Width;
            public int Height;
            public string Scale;
        }
    }
}
