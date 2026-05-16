"""Graph schema — node tables and relationship tables for LadybugDB."""

# Node tables
# PRIMARY KEY is required by LadybugDB for each node table.

SCHEMA_STATEMENTS = [
    # --- Structure nodes ---
    "CREATE NODE TABLE File(path STRING, language STRING, hash STRING, size INT64, PRIMARY KEY(path))",
    "CREATE NODE TABLE Folder(path STRING, PRIMARY KEY(path))",

    # --- Code symbol nodes ---
    "CREATE NODE TABLE Class(id STRING, name STRING, file STRING, implements STRING, docstring STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Interface(id STRING, name STRING, file STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Function(id STRING, name STRING, file STRING, signature STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Method(id STRING, name STRING, class_name STRING, file STRING, signature STRING, visibility STRING, PRIMARY KEY(id))",

    # --- Semantic nodes ---
    "CREATE NODE TABLE Community(id STRING, name STRING, description STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Project(id STRING, name STRING, language STRING, manifest STRING, path STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Process(id STRING, name STRING, entry_point STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE Route(id STRING, path STRING, method STRING, handler STRING, file STRING, PRIMARY KEY(id))",

    # --- Memory nodes (Layer 2, but stored in same graph) ---
    "CREATE NODE TABLE Memory(id STRING, content STRING, category STRING, tier STRING, timestamp DOUBLE, PRIMARY KEY(id))",
    "CREATE NODE TABLE Decision(id STRING, decision STRING, reasoning STRING, active BOOLEAN, timestamp DOUBLE, PRIMARY KEY(id))",

    # --- Relationship tables ---
    "CREATE REL TABLE CONTAINS(FROM Folder TO File)",
    "CREATE REL TABLE PROJECT_CONTAINS(FROM Project TO File)",
    "CREATE REL TABLE FILE_DEFINES_CLASS(FROM File TO Class)",
    "CREATE REL TABLE FILE_DEFINES_INTERFACE(FROM File TO Interface)",
    "CREATE REL TABLE FILE_DEFINES_FUNCTION(FROM File TO Function)",
    "CREATE REL TABLE HAS_METHOD(FROM Class TO Method)",
    "CREATE REL TABLE CALLS(FROM Function TO Function, confidence DOUBLE, reason STRING)",
    "CREATE REL TABLE METHOD_CALLS(FROM Method TO Method, confidence DOUBLE, reason STRING)",
    "CREATE REL TABLE IMPORTS(FROM File TO File)",
    "CREATE REL TABLE EXTENDS(FROM Class TO Class)",
    "CREATE REL TABLE IMPLEMENTS(FROM Class TO Interface)",
    "CREATE REL TABLE MEMBER_OF(FROM Class TO Community)",
    "CREATE REL TABLE FN_MEMBER_OF(FROM Function TO Community)",
    "CREATE REL TABLE STEP_IN(FROM Function TO Process, step_order INT64)",
    "CREATE REL TABLE HANDLES(FROM Function TO Route)",
    "CREATE REL TABLE MEM_REF_CLASS(FROM Memory TO Class)",
    "CREATE REL TABLE MEM_REF_FUNCTION(FROM Memory TO Function)",
    "CREATE REL TABLE MEM_REF_FILE(FROM Memory TO File)",
    "CREATE REL TABLE DEC_ABOUT_CLASS(FROM Decision TO Class)",
    "CREATE REL TABLE DEC_ABOUT_FUNCTION(FROM Decision TO Function)",
    "CREATE REL TABLE DEC_ABOUT_FILE(FROM Decision TO File)",
]
