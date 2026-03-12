# OpenSkills Agency

A minimalistic web application that aggregates agent skills from multiple GitHub repositories into a filterable, sortable table with export feature.

## 🎯 Features

- **Skills Aggregation**: Processes SKILL.md files from locally cloned GitHub repositories
- **Auto-Categorization**: AI-powered tagging system (2-5 tags per skill)
- **Security Scanning**: Cisco AI Defense and Snyk analysis for each skill
- **Offline Capable**: Process skills without internet once repositories are cloned
- **Fast Processing**: No API rate limits - processes hundreds of skills in seconds

## 📋 Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## 🚀 Installation

### Prerequisites

- Python 3.7+
- Git (for cloning repositories)
- jq (optional, for batch update script)

### Setup

1. **Clone this repository**
   ```bash
   git clone <your-repo-url>
   cd skills
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Clone skill repositories** (first time only)
   ```bash
   ./scripts/update-repos.sh
   ```

   **Note:** This step is automatically handled by GitHub Actions in production.
   For local development, you can clone repositories manually or run the update script.

### Optional: Populate Repository Metadata

If `repos.json` doesn't have `stars` and `license` fields populated:

```bash
# Create .env with GitHub token (for metadata script only)
echo "GITHUB_TOKEN=your_token_here" > .env

# Run metadata population script (one-time)
venv/bin/python scripts/populate_metadata.py
```

This is only needed once or when adding new repositories to repos.json.

## 📖 Usage

### 1. Update repositories (optional - handled by GitHub Actions)

To manually update all cloned repositories:

```bash
./scripts/update-repos.sh
```

### 2. Process skills and generate data

Run the Python processor to collect skills from local repositories:

```bash
venv/bin/python main.py
```

This will:
- Scan all locally cloned repositories in `repos/` directory
- Extract metadata (license, commit ID, summary)
- Auto-generate 2-5 tags per skill
- Run security scanners (Cisco AI Defense, Snyk)
- Generate `public/skills-data.json`

**Note:** No GitHub token is required for processing skills. All data is read from local filesystem.


## 📁 Project Structure

```
skills/
├── .gitignore                      # Excludes repos/ and venv/
├── repos.json                      # Repository configurations with metadata
├── categories.json                 # Category keyword definitions
├── main.py                         # Local skills processor (no GitHub API)
├── requirements.txt                # Python dependencies
├── venv/                           # Virtual environment
├── repos/                          # Cloned repositories (gitignored)
│   ├── anthropics/skills/
│   ├── openai/skills/
│   └── ...
├── scripts/
│   ├── populate_metadata.py       # GitHub API utility (optional)
│   ├── update-repo.sh             # Clone/update single repository
│   └── update-repos.sh            # Batch update all repositories
└── public/
    └── skills-data.json           # Generated skills database
```

## 🔄 Workflow

1. **Clone repositories** (manual or via GitHub Actions):
   ```bash
   ./scripts/update-repos.sh
   ```

2. **Process skills locally**:
   ```bash
   venv/bin/python main.py
   ```

3. **Update repository metadata** (optional, when adding new repos):
   ```bash
   venv/bin/python scripts/populate_metadata.py
   ```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
Especially interested in PRs for repos.json and categories.json

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- All the amazing developers and organizations sharing their agent skills
- The open source community for making this possible

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Made with ❤️ by steftux**
