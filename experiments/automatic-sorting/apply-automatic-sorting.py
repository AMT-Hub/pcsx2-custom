"""Extend the accepted manual patch in an isolated source checkout only."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent


def apply(root):
    changes = {}

    def edit(name, old, new, count=1):
        path = root / name
        text = changes.get(path, path.read_text(encoding='utf-8'))
        if text.count(old) != count:
            raise RuntimeError('Unexpected sorting integration: ' + name + ' / ' + old[:80])
        changes[path] = text.replace(old, new)

    h = 'pcsx2/GameList.h'
    c = 'pcsx2/GameList.cpp'
    ui = 'pcsx2-qt/Settings/GameSummaryWidget.cpp'
    edit(h, '#pragma once', '#pragma once\n#include "AutoSortTitle.h"')
    edit(h, '\t\tstd::string custom_sort_title; // Loaded from portable settings, never cached.',
         '\t\tstd::string custom_sort_title; // Manual override; never cached.\n'
         '\t\tstd::string automatic_sort_title; // Catalogue default; never cached.\n'
         '\t\tbool normal_sort_title = false; // Explicit opt-out survives refreshes.')
    edit(h, '''\t\t\tif (!custom_sort_title.empty())
\t\t\t\treturn custom_sort_title;
\t\t\t// If there's a separate EN title, then title_sort is in the wrong language and we can't use it
\t\t\tif (force_en && !title_en.empty())
\t\t\t\treturn title_en;
\t\t\treturn title_sort.empty() ? title : title_sort;''',
         '''\t\t\treturn AutoSortTitle::Resolve(custom_sort_title, normal_sort_title,
\t\t\t\tautomatic_sort_title, title, title_sort, title_en, force_en);''')
    edit(h, 'bool SaveCustomSortTitleForPath(const std::string& path, const std::string& title);',
         'bool SaveCustomSortTitleForPath(const std::string& path, const std::string& title, bool use_automatic = false);')
    edit(c, '''static void LoadCustomSortTitle(GameList::Entry& entry)
{
\tINISettingsInterface settings(SortingTitleFile());
\tentry.custom_sort_title.clear();
\tif (settings.Load())
\t\tentry.custom_sort_title = settings.GetStringValue(SortingTitleKey(entry).c_str(), "SortingTitle", "");
}''', '''static void LoadCustomSortTitle(GameList::Entry& entry)
{
\t// One immutable catalogue per process. Updating it takes effect on restart.
\t// Resources belongs to the active runtime, so update/rollback selects the
\t// matching catalogue without touching the portable manual override file.
\tstatic INISettingsInterface catalogue(Path::Combine(EmuFolders::Resources, "automatic-sorting.ini"));
\tstatic const bool catalogue_loaded = catalogue.Load();
\tentry.automatic_sort_title.clear();
\tif (catalogue_loaded && !entry.serial.empty())
\t{
\t\tstd::string serial = entry.serial;
\t\tfor (char& ch : serial)
\t\t\tif (ch >= 'a' && ch <= 'z') ch = static_cast<char>(ch - 'a' + 'A');
\t\tentry.automatic_sort_title = catalogue.GetStringValue(
\t\t\tfmt::format("{}_{:08X}", serial, entry.crc).c_str(), "SortingTitle", "");
\t\tif (entry.automatic_sort_title.empty())
\t\t\tentry.automatic_sort_title = catalogue.GetStringValue(serial.c_str(), "SortingTitle", "");
\t}
\tINISettingsInterface settings(SortingTitleFile());
\tentry.custom_sort_title.clear();
\tentry.normal_sort_title = false;
\tif (settings.Load())
\t{
\t\tconst std::string key = SortingTitleKey(entry);
\t\tentry.custom_sort_title = settings.GetStringValue(key.c_str(), "SortingTitle", "");
\t\tentry.normal_sort_title = settings.GetBoolValue(key.c_str(), "UseNormalTitle", false);
\t}
}''')
    edit(c, 'bool GameList::SaveCustomSortTitleForPath(const std::string& path, const std::string& title)',
         'bool GameList::SaveCustomSortTitleForPath(const std::string& path, const std::string& title, bool use_automatic)')
    edit(c, '''\tif (title.empty())
\t\tsettings.DeleteValue(key.c_str(), "SortingTitle");
\telse
\t\tsettings.SetStringValue(key.c_str(), "SortingTitle", title.c_str());''',
         '''\tif (use_automatic || title.empty())
\t\tsettings.DeleteValue(key.c_str(), "SortingTitle");
\telse
\t\tsettings.SetStringValue(key.c_str(), "SortingTitle", title.c_str());
\tif (!use_automatic && title.empty())
\t\tsettings.SetBoolValue(key.c_str(), "UseNormalTitle", true);
\telse
\t\tsettings.DeleteValue(key.c_str(), "UseNormalTitle");''')
    edit(c, '''\t\tif (SortingTitleKey(item) == key)
\t\t\titem.custom_sort_title = title;''', '''\t\tif (SortingTitleKey(item) == key)
\t\t{
\t\t\titem.custom_sort_title = use_automatic ? std::string() : title;
\t\t\titem.normal_sort_title = !use_automatic && title.empty();
\t\t}''')
    edit(ui, '#include <QtWidgets/QMessageBox>',
         '#include <QtWidgets/QMessageBox>\n#include <QtWidgets/QMenu>')
    edit(ui, 'm_ui.titleSort->setText(QString::fromStdString(entry->custom_sort_title.empty() ? entry->title_sort : entry->custom_sort_title));',
         '''m_ui.titleSort->setText(entry->normal_sort_title && entry->custom_sort_title.empty() ? QString() : QString::fromStdString(entry->GetTitleSort()));''')
    edit(ui, 'm_ui.titleSort->setPlaceholderText(tr("Use normal title ordering"));',
         '''m_ui.titleSort->setPlaceholderText(tr("Normal title ordering (automatic disabled)"));
\tm_ui.titleSort->setContextMenuPolicy(Qt::CustomContextMenu);
\tconnect(m_ui.titleSort, &QWidget::customContextMenuRequested, this, [this](const QPoint& point) {
\t\tQMenu* menu = m_ui.titleSort->createStandardContextMenu();
\t\tmenu->addSeparator();
\t\tQAction* automatic = menu->addAction(tr("Use automatic sorting title"));
\t\tif (menu->exec(m_ui.titleSort->mapToGlobal(point)) == automatic)
\t\t{
\t\t\tif (GameList::SaveCustomSortTitleForPath(m_entry_path, "", true))
\t\t\t{
\t\t\t\tm_ui.titleSort->setModified(false);
\t\t\t\tg_main_window->refreshGameListTitles();
\t\t\t\trepopulateCurrentDetails();
\t\t\t}
\t\t\telse
\t\t\t\tQMessageBox::warning(this, tr("Sorting Title"), tr("Could not save the sorting title. Check that the portable settings folder is writable."));
\t\t}
\t\tdelete menu;
\t});''')
    edit(ui, 'Controls title sorting without changing the displayed name. Clear this field to restore database/default ordering. Saved automatically when you leave the field. Applies when sorting the game list by title.',
         'Automatic Sorting Titles test1. Catalogue defaults appear automatically. Your edits take priority and survive rescans and updates. Clear to use normal title ordering; right-click and choose Use automatic sorting title to reset. Saved when you leave this field. Display names remain unchanged. Applies when sorting by title.')
    edit('pcsx2-qt/GameList/GameListModel.cpp', '''\treturn QtHost::LocaleSensitiveCompare(QString::fromStdString(left->GetTitleSort(m_prefer_english_titles)),
\t\t\t\tQString::fromStdString(right->GetTitleSort(m_prefer_english_titles))) < 0;''',
         '''\treturn AutoSortTitle::Compare(left->GetTitleSort(m_prefer_english_titles),
\t\tright->GetTitleSort(m_prefer_english_titles), [](std::string_view lhs, std::string_view rhs) {
\t\t\treturn QtHost::LocaleSensitiveCompare(QString::fromUtf8(lhs.data(), lhs.size()),
\t\t\t\tQString::fromUtf8(rhs.data(), rhs.size()));
\t\t}) < 0;''')
    # Validate every replacement before writing any source file.
    target = root / 'pcsx2/AutoSortTitle.h'
    if target.exists():
        raise RuntimeError('Automatic sorting header already exists: ' + str(target))
    for path, text in changes.items():
        path.write_text(text, encoding='utf-8', newline='\n')
    shutil.copyfile(ROOT / 'AutoSortTitle.h', target)
    resources = root / 'bin/resources'
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'automatic-sorting.ini', resources / 'automatic-sorting.ini')


if __name__ == '__main__':
    apply(Path(sys.argv[1]).resolve())
    print('Automatic sorting prototype applied; Windows acceptance is still required.')
