# התחלה מהירה — פיילוט 20 אירועים

המאגר בארכיון ההורדה **ריק בכוונה**: אנחנו לא ממציאים אירועים ולא מציגים דוגמות סינתטיות בתור מחקר אמיתי.

## תנאים מקדימים
- Windows / macOS / Linux + Python 3.11 ומעלה.
- Claude Code / Codex אם רוצים פיתוח וביקורת באמצעות סוכנים.
- גישה לאינטרנט בשביל `collect`. הגישה ל-Federal Register בפיילוט אינה דורשת מפתח לפי התיעוד הציבורי.
- לחשיפה מוגבלת ל-LLM אפשר להפעיל Anthropic API עם מפתח משלך; זה שירות בתשלום בנפרד.
- מומלץ לעבוד ב-Git repo ולשמור עותקי מקור גם באחסון עם versioning.

## פקודות — PowerShell / Terminal, מתיקיית הפרויקט

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m radar --help
```

### פיילוט מקוון (נתוני מקור אמיתיים בלבד)

בחרי מראש חלון תאריכים היסטורי קטן, ורשמי אותו ביומן המחקר לפני ההרצה. דוגמה להדגמת *הפקודה בלבד*:

```powershell
python -m radar collect --start 2022-04-01 --end 2022-04-10 --max-pages 2 --max-docs 100
python -m radar screen
python -m radar extract --backend heuristic --limit 30
python -m radar audit
```

**מגבלה:** `heuristic` מחלץ אותות בלבד ולא מסוגל לאשר קבוצה מושפעת. אי אפשר לקבל ממנו 20 רשומות מאושרות ללא השלמה מבוקרת של חילוץ, אימות והכרעה אנושית. מומלץ להשתמש ב-API extract עם `--backend anthropic` *לפני* הרצת heuristic על אותם IDs, אם הוגדר מפתח; לחלופין ניתן להוסיף תהליך עריכה אנושי מבוקר. לא להחליף את הקבצים בשקט.

### חילוץ אופציונלי ב-API של Anthropic

```powershell
python -m pip install -e ".[ai]"
$env:ANTHROPIC_API_KEY="YOUR_KEY"
$env:ANTHROPIC_MODEL="MODEL_AVAILABLE_TO_YOUR_ACCOUNT"
python -m radar extract --backend anthropic --limit 30
```

הקריאה יכולה לעלות כסף. הסוכן לא ניגש לאינטרנט אבל מודל מאומן עלול להכיר מידע מאוחר; לכן זהו חילוץ טענות מהמסמך בלבד, לא סימולציה עיוורת מושלמת.

### ביקורת מסמכים שנפסלו

חובה לדגום גם מתוך המסמכים שלא עברו את המסנן, אחרי שיש כאלה:

```powershell
python -m radar negative-sample --size 20 --seed 26023 --name negative-audit-20
```

הפקודה מפיקה רשימת ביקורת; היא **לא מסווגת את המקרים בעצמה**. יש לבדוק כל מסמך שנדגם ולתעד כמה אירועים אמיתיים הוחמצו. אם אין 20 מסמכים שליליים הפקודה תיכשל במקום להמציא מקרים.

### בדיקה ואישור ידניים

פתחי `data/candidates/*.json`, בדקי את ה-PDF/טקסט של המקור בארכיון המקורי ואת תאריך הפרסום, ודאי שכל הציטוטים **מוכיחים משמעותית** את הטענות ולא רק מופיעים בטקסט. העבירי את המקרה לסוכן verifier ולאחר מכן הכריעי בעצמך.

```powershell
python -m radar validate --event-id federal-register-DOCUMENT-ID
python -m radar review --event-id federal-register-DOCUMENT-ID --decision accept --reviewer "YOUR NAME" --reason "Verified historic original and direct quotes independently" --source-original-verified --date-verified --change-key "unique-underlying-change"
```

אין להפעיל flags של אימות אוטומטית על כל הרשומות. אם לא אומת — `--decision reject` עם הסבר.

### מדגם והקפאה (רק לאחר שאושרו לפחות 20 אירועים)

```powershell
python -m radar sample --size 20 --seed 26023 --name pilot-20
python -m radar verify-sample --name pilot-20
python -m radar freeze --name pilot-20
python -m radar verify-freeze --name pilot-20
python -m radar audit
```

`--final` חסום בכוונה, עד שיבוצעו ביקורת מסגרת דגימה ופתיחת מחברים נוספים. בלי זה 150 אירועים אינם מדגם שאפשר להסיק ממנו על מגוון השווקים.

## פתיחה ב-Claude Code וב-Codex

1. פתחי את התיקייה עצמה (לא תיקיית ZIP) ב-IDE או בטרמינל.
2. הפעלי Claude Code מתוך שורש הפרויקט; הוא קורא `CLAUDE.md` ואת תת-הסוכנים ב-`.claude/agents/`.
3. מסרי לו את ההנחיה הראשונה מ-`PROMPTS.md`.
4. פתחי Codex בנפרד, על ענף/Worktree נפרד, והדביקי את ההנחיה מ-`.codex/prompts/independent-audit.md`.
5. לא לתת לשני כלים לערוך במקביל את אותם נתוני מקור וקבצי הקפאה.

## שימי לב
הארכיטקטורה והתיעוד אינם 'הרצת מחקר' או הוכחה לחיזוי ביקוש. לפני מסקנות מדעיות נחוצה ביקורת מקור, דגימה וניתוח תוצאות נפרד.
