#include <string>
#include <cassert>
struct Entry { std::string title, title_sort, title_en, custom_sort_title;
		const std::string& GetTitleSort(bool force_en = false) const
		{
			if (!custom_sort_title.empty())
				return custom_sort_title;
			// If there's a separate EN title, then title_sort is in the wrong language and we can't use it
			if (force_en && !title_en.empty())
				return title_en;
			return title_sort.empty() ? title : title_sort;
		}
};
int main(){
Entry e{"TimeSplitters: Future Perfect", "", "", ""};
assert(e.GetTitleSort()==e.title);
e.custom_sort_title="TimeSplitters 3";
assert(e.GetTitleSort()=="TimeSplitters 3");
assert(e.title=="TimeSplitters: Future Perfect");
e.title_sort="database";e.title_en="English";
assert(e.GetTitleSort(true)=="TimeSplitters 3");
e.custom_sort_title.clear();
assert(e.GetTitleSort()=="database");assert(e.GetTitleSort(true)=="English");
e.title_sort.clear();assert(e.GetTitleSort()==e.title);
}
