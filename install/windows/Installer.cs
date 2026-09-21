using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;

class Installer
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        try
        {
            string executable = Assembly.GetExecutingAssembly().Location;
            if (args.Length == 2 && args[0] == "--extract")
            {
                // Build validation: extract only, never start services or create users.
                Extract(Path.GetFullPath(args[1]));
                return 0;
            }
            if (args.Length == 1 && args[0] == "--start")
                return Run(Path.GetDirectoryName(executable), "start.ps1");

            Console.WriteLine("AGRO-AI-PRO — Instalação de teste\n");
            Console.WriteLine("Requer Docker Desktop iniciado, com containers Linux, e internet.");
            Console.WriteLine("Será criado um ambiente vazio e separado dos seus dados atuais.");
            Console.WriteLine("A primeira preparação pode levar vários minutos.");
            Console.Write("\nPressione ENTER para instalar ou feche esta janela para cancelar: ");
            Console.ReadLine();
            string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "AGRO-AI-PRO", "Teste-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 6));
            Extract(root);
            File.Copy(executable, Path.Combine(root, "AGRO-AI-PRO.exe"));
            Console.WriteLine("\nArquivos instalados em: " + root);
            return Run(root, "install.ps1");
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Não foi possível concluir: " + ex.Message);
            Console.WriteLine("Pressione ENTER para fechar.");
            Console.ReadLine();
            return 1;
        }
    }

    static void Extract(string root)
    {
        if (Directory.Exists(root)) throw new IOException("A pasta de destino já existe. Nenhum arquivo foi substituído.");
        Directory.CreateDirectory(root);
        string prefix = root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        using (Stream input = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
        using (ZipArchive zip = new ZipArchive(input, ZipArchiveMode.Read))
        {
            foreach (ZipArchiveEntry item in zip.Entries)
            {
                string target = Path.GetFullPath(Path.Combine(root, item.FullName));
                if (!target.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("Caminho inválido no pacote.");
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                using (Stream source = item.Open())
                using (FileStream dest = new FileStream(target, FileMode.CreateNew)) source.CopyTo(dest);
            }
        }
    }

    static int Run(string root, string script)
    {
        string shell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
            "WindowsPowerShell", "v1.0", "powershell.exe");
        ProcessStartInfo info = new ProcessStartInfo(shell,
            "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(root, "desktop", script) + "\"");
        info.WorkingDirectory = root;
        info.UseShellExecute = false;
        // Windows PowerShell must discover its own modules, even when launched
        // from a host with a PowerShell 7 module path.
        info.EnvironmentVariables.Remove("PSModulePath");
        using (Process child = Process.Start(info)) { child.WaitForExit(); return child.ExitCode; }
    }
}
