# 📝 Git Commands to Push ArthaNethra to GitHub

## Step 1: Review What We've Built

Check all the files that will be committed:

```bash
# View all files
ls -la

# Count total files
find . -type f | grep -v node_modules | grep -v .git | wc -l
```

---

## Step 2: Initialize Git Repository

```bash
# Initialize git (if not already done)
git init

# Check git status
git status
```

---

## Step 3: Add All Files

```bash
# Add all files to staging
git add .

# Verify what will be committed
git status
```

---

## Step 4: Create Initial Commit

```bash
# Create commit with descriptive message
git commit -m "🚀 Initial commit: ArthaNethra - AI Financial Risk Investigator

- Complete FastAPI backend with 6 core services
- Angular 19 frontend with 5 main components
- Docker infrastructure (Weaviate, Neo4j)
- LandingAI ADE integration
- AWS Bedrock Claude 3 chatbot
- Comprehensive documentation
- Production-ready architecture

Built for Financial AI Hackathon Championship 2025"
```

---

## Step 5: Set Main Branch

```bash
# Rename branch to main
git branch -M main
```

---

## Step 6: Add Remote Origin

```bash
# Add GitHub remote
git remote add origin https://github.com/devieswar/ArthaNethra.git

# Verify remote
git remote -v
```

---

## Step 7: Push to GitHub

```bash
# Push to GitHub (first time)
git push -u origin main
```

**Note:** You may be prompted for GitHub credentials or to authenticate via browser.

---

## Alternative: If Repository Already Exists

If the repository already has content:

```bash
# Pull existing content first
git pull origin main --allow-unrelated-histories

# Resolve any conflicts if needed
# Then push
git push -u origin main
```

---

## Step 8: Verify on GitHub

1. Visit https://github.com/devieswar/ArthaNethra
2. Verify all files are present
3. Check README renders correctly
4. Review file structure

---

## Future Commits

For future changes:

```bash
# Check status
git status

# Add changed files
git add .

# Commit with message
git commit -m "feat: your feature description"

# Push
git push
```

---

## Commit Message Conventions

Use semantic commit messages:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Adding tests
- `chore:` — Maintenance tasks

**Examples:**
```bash
git commit -m "feat: add risk threshold configuration"
git commit -m "fix: resolve Neo4j connection timeout"
git commit -m "docs: update API documentation"
```

---

## Branches (Optional)

For feature development:

```bash
# Create feature branch
git checkout -b feature/graph-visualization

# Work on feature...

# Commit changes
git add .
git commit -m "feat: implement Sigma.js graph visualization"

# Push feature branch
git push -u origin feature/graph-visualization

# Create Pull Request on GitHub

# After merge, switch back to main
git checkout main
git pull
```

---

## .gitignore Check

Verify sensitive files are ignored:

```bash
# Check .gitignore
cat .gitignore

# Ensure these are NOT committed:
# - .env (your actual API keys)
# - node_modules/
# - __pycache__/
# - *.pyc
# - uploads/
# - cache/
```

---

## GitHub Repository Settings

After pushing, configure on GitHub:

1. **Description**
   > AI-powered financial investigation platform using LandingAI ADE, AWS Bedrock, and knowledge graphs

2. **Topics** (add tags)
   - `financial-ai`
   - `knowledge-graph`
   - `risk-detection`
   - `fastapi`
   - `angular`
   - `aws-bedrock`
   - `landingai`
   - `hackathon`

3. **README**
   - Verify it renders correctly
   - Check all links work

4. **License**
   - Confirm MIT license is visible

---

## GitHub Actions (Optional)

For CI/CD, create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest
```

---

## Security: Protecting API Keys

**⚠️ CRITICAL: Never commit API keys!**

If you accidentally committed `.env`:

```bash
# Remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin main --force
```

Then:
1. Rotate all API keys immediately
2. Add `.env` to `.gitignore`
3. Commit the fix

---

## Hackathon Submission

When submitting:

1. ✅ Code pushed to GitHub
2. ✅ README is comprehensive
3. ✅ Documentation is complete
4. ✅ No API keys in repo
5. ✅ License file included
6. ✅ Clear setup instructions

**Repository URL for submission:**
```
https://github.com/devieswar/ArthaNethra
```

---

## Collaborators (Optional)

To add team members:

1. Go to repository Settings
2. Click "Collaborators"
3. Add by GitHub username
4. They can then:
```bash
git clone https://github.com/devieswar/ArthaNethra.git
cd ArthaNethra
git checkout -b their-feature-branch
```

---

## Tags for Releases

Create version tags:

```bash
# Tag v1.0.0 (hackathon submission)
git tag -a v1.0.0 -m "Hackathon submission version"

# Push tags
git push origin v1.0.0

# Or push all tags
git push --tags
```

---

## Final Checklist

Before pushing:

- [ ] `.env` is in `.gitignore`
- [ ] No API keys in code
- [ ] README is complete
- [ ] Documentation is thorough
- [ ] Code is clean and commented
- [ ] Docker setup works
- [ ] All sensitive data excluded

---

**You're ready to push! 🚀**

Run the commands in order and your project will be live on GitHub!

