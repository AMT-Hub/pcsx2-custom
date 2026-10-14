"""Apply the isolated sorting-title addition to pinned PCSX2 2.8.2."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def edit(name, old, new):
 p=root/name;s=p.read_text(encoding='utf-8')
 if s.count(old)!=1:raise RuntimeError('Unexpected source: '+name+' / '+old[:70])
 p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

h='pcsx2/GameList.h';c='pcsx2/GameList.cpp';ui='pcsx2-qt/Settings/GameSummaryWidget.cpp'
edit(h,'\t\tstd::string title_sort;','\t\tstd::string title_sort;\n\t\tstd::string custom_sort_title; // Loaded from portable settings, never cached.')
edit(h,'\t\t\t// If there\'s a separate EN title', '\t\t\tif (!custom_sort_title.empty())\n\t\t\t\treturn custom_sort_title;\n\t\t\t// If there\'s a separate EN title')
edit(h,'\tvoid SaveCustomTitleForPath(', '\tbool SaveCustomSortTitleForPath(const std::string& path, const std::string& title);\n\tvoid SaveCustomTitleForPath(')
helpers=r'''
// Independent of display titles and emulator game settings. Disc identity remains
// stable when portable installations and ROM folders change drive or location.
static std::string SortingTitleKey(const GameList::Entry& entry)
{
	if (!entry.serial.empty() && entry.crc != 0)
		return fmt::format("{}_{:08X}", entry.serial, entry.crc);
	std::string key = "Path-";
	for (const unsigned char ch : entry.path)
		key += fmt::format("{:02X}", ch);
	return key;
}

static std::string SortingTitleFile()
{
	return Path::Combine(EmuFolders::Settings, "sorting-titles.ini");
}

static void LoadCustomSortTitle(GameList::Entry& entry)
{
	INISettingsInterface settings(SortingTitleFile());
	entry.custom_sort_title.clear();
	if (settings.Load())
		entry.custom_sort_title = settings.GetStringValue(SortingTitleKey(entry).c_str(), "SortingTitle", "");
}

bool GameList::SaveCustomSortTitleForPath(const std::string& path, const std::string& title)
{
	auto lock = GetLock();
	const Entry* entry = GetEntryForPath(path.c_str());
	if (!entry)
		return false;
	const std::string key = SortingTitleKey(*entry);
	const std::string filename = SortingTitleFile();
	INISettingsInterface settings(filename);
	if (!settings.Load() && FileSystem::FileExists(filename.c_str()))
		return false; // Preserve an existing unreadable file.
	if (title.empty())
		settings.DeleteValue(key.c_str(), "SortingTitle");
	else
		settings.SetStringValue(key.c_str(), "SortingTitle", title.c_str());
	if (!settings.Save())
		return false;
	for (Entry& item : s_entries)
	{
		if (SortingTitleKey(item) == key)
			item.custom_sort_title = title;
	}
	return true;
}

'''
edit(c,'bool GameList::AddFileFromCache(',helpers+'bool GameList::AddFileFromCache(')
# Both cold scan and warm cache must load overrides; cache format stays unchanged.
p=root/c;s=p.read_text();needle='\ts_entries.push_back(std::move(entry));'
assert s.count(needle)==2
p.write_text(s.replace(needle,'\tLoadCustomSortTitle(entry);\n'+needle),encoding='utf-8',newline='\n')
edit(ui,'m_ui.titleSort->setText(QString::fromStdString(entry->title_sort));','m_ui.titleSort->setText(QString::fromStdString(entry->custom_sort_title.empty() ? entry->title_sort : entry->custom_sort_title));\n\tm_ui.titleSort->setModified(false);')
edit(ui,'m_ui.detailsFormLayout->setRowVisible(row, !entry->title_sort.empty());','m_ui.detailsFormLayout->setRowVisible(row, true);')
edit(ui,'\tpopulateTrackList(entry);','''\tpopulateTrackList(entry);

	m_ui.titleSort->setReadOnly(false);
	m_ui.titleSort->setPlaceholderText(tr("Use normal title ordering"));
	m_ui.titleSort->setToolTip(tr("Controls title sorting without changing the displayed name. Clear this field to restore database/default ordering. Saved automatically when you leave the field. Applies when sorting the game list by title."));
	connect(m_ui.titleSort, &QLineEdit::editingFinished, this, [this]() {
		if (!m_ui.titleSort->isModified())
			return;
		const std::string title = m_ui.titleSort->text().trimmed().toStdString();
		if (!GameList::SaveCustomSortTitleForPath(m_entry_path, title))
		{
			QMessageBox::warning(this, tr("Sorting Title"), tr("Could not save the sorting title. Check that the portable settings folder is writable."));
			return;
		}
		m_ui.titleSort->setModified(false);
		g_main_window->refreshGameListTitles();
		repopulateCurrentDetails();
	});''')
edit('pcsx2-qt/MainWindow.h', '\tvoid rescanFile(const std::string& path);', '\tvoid rescanFile(const std::string& path);\n\tvoid refreshGameListTitles();')
edit('pcsx2-qt/MainWindow.cpp', 'void MainWindow::rescanFile(', 'void MainWindow::refreshGameListTitles()\n{\n\tm_game_list_widget->refreshTitles();\n}\n\nvoid MainWindow::rescanFile(')
edit('pcsx2-qt/GameList/GameListWidget.h', '\tvoid rescanFile(const std::string& path);', '\tvoid rescanFile(const std::string& path);\n\tvoid refreshTitles();')
edit('pcsx2-qt/GameList/GameListWidget.cpp', 'void GameListWidget::rescanFile(', 'void GameListWidget::refreshTitles()\n{\n\tm_model->refresh();\n}\n\nvoid GameListWidget::rescanFile(')
print('Sorting-title patch applied.')
