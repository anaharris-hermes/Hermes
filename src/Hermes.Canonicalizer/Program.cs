using System.Text;
using System.Xml.Linq;
using Microsoft.Data.Sqlite;

const string TeiUrl = "https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/master/data/tlg0059/tlg030/tlg0059.tlg030.perseus-grc2.xml";
const string CanonicalPrefix = "urn:cts:greekLit:tlg0059.tlg030.perseus-grc2:";
var outputDir = Path.GetFullPath(Path.Combine(
    AppContext.BaseDirectory,
    "..",
    "..",
    "..",
    "..",
    "..",
    "data",
    "plato",
    "republic"));
Directory.CreateDirectory(outputDir);
var dbPath = Path.Combine(outputDir, "republic.db");

if (File.Exists(dbPath))
{
    File.Delete(dbPath);
}

using var http = new HttpClient();
await using var teiStream = await http.GetStreamAsync(TeiUrl);
var doc = await XDocument.LoadAsync(teiStream, LoadOptions.None, CancellationToken.None);

XNamespace tei = "http://www.tei-c.org/ns/1.0";
var body = doc.Descendants(tei + "body").Single();

await using var connection = new SqliteConnection($"Data Source={dbPath}");
await connection.OpenAsync();

await using (var create = connection.CreateCommand())
{
    create.CommandText = """
        CREATE TABLE Chunk (
            ChunkId TEXT PRIMARY KEY,
            Sequence INTEGER NOT NULL,
            MilestoneRef TEXT NOT NULL,
            CanonicalRef TEXT NOT NULL,
            GreekText TEXT NOT NULL
        );

        CREATE UNIQUE INDEX UX_Chunk_Sequence ON Chunk(Sequence);
        CREATE INDEX IX_Chunk_MilestoneRef ON Chunk(MilestoneRef);
        CREATE INDEX IX_Chunk_CanonicalRef ON Chunk(CanonicalRef);
        """;

    await create.ExecuteNonQueryAsync();
}

var sequence = 0;
var inserted = 0;
string? firstMilestoneRef = null;
string? lastMilestoneRef = null;
string? activeMilestoneRef = null;
var buffer = new StringBuilder();
var milestoneCount = body
    .Descendants(tei + "milestone")
    .Count(e =>
        string.Equals((string?)e.Attribute("unit"), "section", StringComparison.OrdinalIgnoreCase) &&
        string.Equals((string?)e.Attribute("resp"), "Stephanus", StringComparison.OrdinalIgnoreCase)
    );

Console.WriteLine($"Detected section milestones in TEI: {milestoneCount}");

foreach (var node in body.DescendantNodes())
{
    if (node is XElement element &&
        element.Name == tei + "milestone" &&
        string.Equals((string?)element.Attribute("unit"), "section", StringComparison.OrdinalIgnoreCase) &&
        string.Equals((string?)element.Attribute("resp"), "Stephanus", StringComparison.OrdinalIgnoreCase))
    {
        if (!string.IsNullOrWhiteSpace(activeMilestoneRef))
        {
            var greekText = NormalizeWhitespace(buffer.ToString());
            if (!string.IsNullOrWhiteSpace(greekText))
            {
                await InsertChunkAsync(connection, sequence, activeMilestoneRef, CanonicalPrefix + activeMilestoneRef, greekText);
                inserted++;
                firstMilestoneRef ??= activeMilestoneRef;
                lastMilestoneRef = activeMilestoneRef;
                sequence++;
            }
        }

        activeMilestoneRef = ((string?)element.Attribute("n"))?.Trim();
        buffer.Clear();
        continue;
    }

    if (node is XText textNode && !string.IsNullOrWhiteSpace(activeMilestoneRef))
    {
        buffer.Append(textNode.Value);
        buffer.Append(' ');
    }
}

if (!string.IsNullOrWhiteSpace(activeMilestoneRef))
{
    var finalGreekText = NormalizeWhitespace(buffer.ToString());
    if (!string.IsNullOrWhiteSpace(finalGreekText))
    {
        await InsertChunkAsync(connection, sequence, activeMilestoneRef, CanonicalPrefix + activeMilestoneRef, finalGreekText);
        inserted++;
        firstMilestoneRef ??= activeMilestoneRef;
        lastMilestoneRef = activeMilestoneRef;
    }
}

Console.WriteLine($"total chunks inserted: {inserted}");
Console.WriteLine($"first MilestoneRef: {firstMilestoneRef ?? "(none)"}");
Console.WriteLine($"last MilestoneRef: {lastMilestoneRef ?? "(none)"}");

static async Task InsertChunkAsync(
    SqliteConnection connection,
    int sequence,
    string milestoneRef,
    string canonicalRef,
    string greekText)
{
    await using var insert = connection.CreateCommand();
    insert.CommandText = """
        INSERT INTO Chunk (ChunkId, Sequence, MilestoneRef, CanonicalRef, GreekText)
        VALUES (@chunkId, @sequence, @milestoneRef, @canonicalRef, @greekText);
        """;
    insert.Parameters.AddWithValue("@chunkId", Guid.NewGuid().ToString());
    insert.Parameters.AddWithValue("@sequence", sequence);
    insert.Parameters.AddWithValue("@milestoneRef", milestoneRef);
    insert.Parameters.AddWithValue("@canonicalRef", canonicalRef);
    insert.Parameters.AddWithValue("@greekText", greekText);
    await insert.ExecuteNonQueryAsync();
}

static string NormalizeWhitespace(string input)
{
    if (string.IsNullOrWhiteSpace(input))
        return string.Empty;

    return input
        .Replace("\r", " ")
        .Replace("\n", " ")
        .Trim();
}
