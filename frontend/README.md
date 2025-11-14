# Frontend README

## Local File Search Agent - Frontend

A lightweight, modern web interface for the Local File Search Agent.

### Features

- 🎨 Clean, modern UI with smooth animations
- 💬 Real-time chat interface
- 📱 Responsive design (works on desktop & mobile)
- 🔌 Automatic backend connection monitoring
- 📄 Document management panel
- ⚡ Fast and lightweight (no heavy frameworks)
- 🎯 Keyboard shortcuts for power users

### Quick Start

1. **Start the Backend** (in main folder):
   ```bash
   python api_server.py
   ```

2. **Open the Frontend**:
   - Simply double-click `index.html` in your browser
   - Or use a local server:
     ```bash
     # Python
     python -m http.server 8080
     
     # Then open: http://localhost:8080
     ```

### Project Structure

```
frontend/
├── index.html      # Main HTML structure
├── styles.css      # All styling (CSS variables, components)
├── app.js          # JavaScript logic (API calls, UI updates)
└── README.md       # This file
```

### Technology Stack

- **HTML5** - Semantic markup
- **CSS3** - Modern styling with CSS Grid & Flexbox
- **Vanilla JavaScript** - No frameworks, pure JS
- **Font Awesome** - Icons (CDN)
- **Fetch API** - Backend communication

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift + Enter` - New line in input
- `Ctrl/Cmd + K` - Focus input
- `Ctrl/Cmd + L` - Clear chat
- `Escape` - Close modals

### Customization

#### Change Colors

Edit CSS variables in `styles.css`:

```css
:root {
    --primary-color: #2563eb;  /* Main blue */
    --success-color: #10b981;  /* Green */
    --danger-color: #ef4444;   /* Red */
    /* ... more variables */
}
```

#### Change API URL

Click the settings icon (⚙️) and update the API URL, or edit in browser console:

```javascript
config.apiUrl = 'http://your-api-url:8765';
saveConfig();
```

### Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ⚠️ IE11 (not supported)

### Troubleshooting

**Backend not connecting:**
1. Make sure `api_server.py` is running
2. Check the console for errors (F12)
3. Verify API URL in settings
4. Check firewall/antivirus

**Styles not loading:**
1. Clear browser cache (Ctrl+F5)
2. Check file paths are correct
3. Ensure all files are in the same folder

### Future Enhancements

- [ ] Voice input support
- [ ] File drag & drop for indexing
- [ ] Dark mode toggle
- [ ] Export chat history
- [ ] Markdown rendering in messages
- [ ] Code syntax highlighting
- [ ] WebSocket streaming for real-time responses

### License

Same as main project

### Support

For issues or questions, please check the main project README or open an issue on GitHub.
