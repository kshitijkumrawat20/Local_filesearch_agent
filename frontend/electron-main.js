const { app, BrowserWindow, Tray, Menu } = require('electron');
const path = require('path');

let mainWindow;
let tray;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        },
        title: 'LEKHA - Ram Dhari Fintech',
        backgroundColor: '#f8fafc',
        show: false
    });
    mainWindow.loadFile('index.html');
    mainWindow.once('ready-to-show', () => { mainWindow.show(); });
    mainWindow.on('close', (e) => {
        if (!app.isQuitting) { e.preventDefault(); mainWindow.hide(); }
    });
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {});
app.on('activate', () => {
    if (mainWindow === null) createWindow(); else mainWindow.show();
});
app.on('before-quit', () => { app.isQuitting = true; });
