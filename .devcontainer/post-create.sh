
curl -fsSL https://claude.ai/install.sh | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

sudo npm install -g @fission-ai/openspec@latest
openspec init