Download the wikipedia embeddings from here: https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip and unzip it in the `/src/sample-data` folder.

In Windows with powershell:

```powershell
Invoke-WebRequest -Uri "https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip" -OutFile "vector_database_wikipedia_articles_embedded.zip" 
```

or on Linux/MacOS with wget

```bash
wget https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip
```

Then unzip its content in the src/sample-data folder.

In Windows with powershell:

```powershell
Expand-Archive .\vector_database_wikipedia_articles_embedded.zip .
```

or on Linux/MacOS with unzip:

```bash
unzip ./vector_database_wikipedia_articles_embedded.zip
```

