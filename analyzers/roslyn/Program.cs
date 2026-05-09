using System.Text.Json;
using Microsoft.Build.Locator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.MSBuild;

MSBuildLocator.RegisterDefaults();

var target = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();
var results = new List<Dictionary<string, object>>();

Workspace workspace;
IEnumerable<Project> projects;

if (target.EndsWith(".sln"))
{
    var ws = MSBuildWorkspace.Create();
    var solution = await ws.OpenSolutionAsync(target);
    projects = solution.Projects;
    workspace = ws;
}
else if (target.EndsWith(".csproj"))
{
    var ws = MSBuildWorkspace.Create();
    var project = await ws.OpenProjectAsync(target);
    projects = new[] { project };
    workspace = ws;
}
else
{
    // Find .sln or .csproj in directory
    var sln = Directory.GetFiles(target, "*.sln", SearchOption.TopDirectoryOnly).FirstOrDefault();
    var csproj = Directory.GetFiles(target, "*.csproj", SearchOption.AllDirectories).FirstOrDefault();
    var ws = MSBuildWorkspace.Create();
    if (sln != null)
    {
        var solution = await ws.OpenSolutionAsync(sln);
        projects = solution.Projects;
    }
    else if (csproj != null)
    {
        var project = await ws.OpenProjectAsync(csproj);
        projects = new[] { project };
    }
    else
    {
        Console.Error.WriteLine("No .sln or .csproj found");
        Environment.Exit(1);
        return;
    }
    workspace = ws;
}

foreach (var project in projects)
{
    var compilation = await project.GetCompilationAsync();
    if (compilation == null) continue;

    foreach (var tree in compilation.SyntaxTrees)
    {
        var root = await tree.GetRootAsync();
        var semanticModel = compilation.GetSemanticModel(tree);
        var filePath = tree.FilePath;

        if (string.IsNullOrEmpty(filePath)) continue;

        var fileResult = new Dictionary<string, object>
        {
            ["file"] = filePath,
            ["project"] = project.Name,
            ["classes"] = new List<object>(),
            ["functions"] = new List<string>(),
            ["imports"] = new List<string>()
        };

        // Imports
        var usings = root.DescendantNodes().OfType<UsingDirectiveSyntax>();
        foreach (var u in usings)
            ((List<string>)fileResult["imports"]).Add(u.ToString().Trim());

        // Classes, interfaces, structs
        var typeDecls = root.DescendantNodes().OfType<TypeDeclarationSyntax>();
        foreach (var typeDecl in typeDecls)
        {
            var symbol = semanticModel.GetDeclaredSymbol(typeDecl);
            if (symbol == null) continue;

            var classInfo = new Dictionary<string, object>
            {
                ["name"] = symbol.Name,
                ["kind"] = typeDecl switch
                {
                    ClassDeclarationSyntax => "class",
                    InterfaceDeclarationSyntax => "interface",
                    StructDeclarationSyntax => "struct",
                    RecordDeclarationSyntax => "record",
                    _ => "type"
                },
                ["methods"] = new List<string>()
            };

            // Base types
            var bases = new List<string>();
            if (symbol.BaseType != null && symbol.BaseType.Name != "Object")
                bases.Add(symbol.BaseType.Name);
            foreach (var iface in symbol.Interfaces)
                bases.Add(iface.Name);
            if (bases.Count > 0)
                classInfo["implements"] = string.Join(", ", bases);

            // Methods
            var methods = typeDecl.Members.OfType<MethodDeclarationSyntax>();
            foreach (var method in methods)
            {
                var methodSymbol = semanticModel.GetDeclaredSymbol(method);
                if (methodSymbol == null) continue;
                var returnType = methodSymbol.ReturnType.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat);
                var parameters = string.Join(", ", methodSymbol.Parameters.Select(p =>
                    $"{p.Type.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat)} {p.Name}"));
                ((List<string>)classInfo["methods"]).Add($"{returnType} {methodSymbol.Name}({parameters})");
            }

            // Constructors
            var ctors = typeDecl.Members.OfType<ConstructorDeclarationSyntax>();
            foreach (var ctor in ctors)
            {
                var ctorSymbol = semanticModel.GetDeclaredSymbol(ctor);
                if (ctorSymbol == null) continue;
                var parameters = string.Join(", ", ctorSymbol.Parameters.Select(p =>
                    $"{p.Type.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat)} {p.Name}"));
                ((List<string>)classInfo["methods"]).Add($"{symbol.Name}({parameters})");
            }

            ((List<object>)fileResult["classes"]).Add(classInfo);
        }

        // Top-level functions (C# 9+ top-level statements with local functions)
        var localFunctions = root.DescendantNodes().OfType<LocalFunctionStatementSyntax>()
            .Where(f => f.Parent is GlobalStatementSyntax || f.Parent is CompilationUnitSyntax);
        foreach (var fn in localFunctions)
        {
            ((List<string>)fileResult["functions"]).Add(fn.Identifier.Text);
        }

        // Only include files with content
        if (((List<object>)fileResult["classes"]).Count > 0 ||
            ((List<string>)fileResult["functions"]).Count > 0)
        {
            results.Add(fileResult);
        }
    }
}

var json = JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = false });
Console.WriteLine(json);
