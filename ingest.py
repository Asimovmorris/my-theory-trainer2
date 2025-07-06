import pathlib, re, datetime, sqlite3, sys
import pdfplumber, docx

DB = "data/theory.db"
conn = sqlite3.connect(DB)
conn.execute("""CREATE TABLE IF NOT EXISTS concepts(
                   id INTEGER PRIMARY KEY,
                   concept TEXT, definition TEXT, category TEXT,
                   source TEXT, added DATE)""")

def parse_blocks(text):
    # Matches "Heading (optional year): Definition text..."
    pattern = re.compile(r"^(?P<concept>[A-Z].+?):\s*(?P<def>.+)$", re.M)
    for m in pattern.finditer(text):
        yield m["concept"].strip(), m["def"].strip()

def extract(path):
    if path.suffix.lower()==".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())
    elif path.suffix.lower() in [".docx", ".doc"]:
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return path.read_text()

def ingest(path):
    text = extract(path)
    for concept, definition in parse_blocks(text):
        print(f"\n{concept}  ->  {definition[:80]}...")
        choice = input("[A]ccept / [E]dit / [S]kip ? ").strip().lower()[:1] or "a"
        if choice == "s": continue
        if choice == "e":
            concept = input("New concept: ") or concept
            definition = input("New definition: ") or definition
        category = ("Writing","Research","Stats")[
            int(input("Pick category 0-Writing 1-Research 2-Stats: ") or 1)]
        conn.execute("INSERT INTO concepts(concept,definition,category,source,added)"
                     " VALUES(?,?,?,?,?)",
                     (concept, definition, category, path.name, datetime.date.today()))
        conn.commit()

if __name__ == "__main__":
    files = sys.argv[1:] or pathlib.Path("sample_files").glob("*")
    for f in files: ingest(pathlib.Path(f))
    print("✅  Done.")
