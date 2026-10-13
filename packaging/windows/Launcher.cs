using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class AgroLauncher {
    [STAThread]
    static int Main(string[] args) {
        try {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            var start = new ProcessStartInfo {
                FileName = Path.Combine(root, "runtime", "python.exe"),
                Arguments = "\"" + Path.Combine(root, "desktop_runtime.py") + "\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            // Somente switches internos de validação, sem comando arbitrário.
            foreach (string arg in args) {
                if (arg == "--smoke-test" || arg == "--window-test") start.Arguments += " " + arg;
            }
            start.EnvironmentVariables["AGRO_PACKAGE_RESOURCES"] = root;
            start.EnvironmentVariables["TCL_LIBRARY"] = Path.Combine(root, "runtime", "tcl", "tcl8.6");
            start.EnvironmentVariables["TK_LIBRARY"] = Path.Combine(root, "runtime", "tcl", "tk8.6");
            start.EnvironmentVariables.Remove("PYTHONHOME");
            start.EnvironmentVariables.Remove("PYTHONPATH");
            using (var process = Process.Start(start)) {
                process.StandardInput.Close();
                process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) {};
                process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) {};
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                process.WaitForExit();
                return process.ExitCode;
            }
        } catch (Exception) {
            MessageBox.Show("Não foi possível iniciar o AGRO. Reinstale o pacote de testes.", "AGRO-AI-PRO Testes", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
