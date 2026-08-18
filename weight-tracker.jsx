import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Plus, Trash2, Scale, Flame, Dumbbell, Pencil, Check, NotebookPen, TrendingUp,
  ChevronRight, Camera, Loader2, Sparkles, X, Activity, PieChart, UserCheck,
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ComposedChart, Bar } from 'recharts';

const DEFAULT_USERS = [
  { id: 'u1', name: '使用者一' },
  { id: 'u2', name: '使用者二' },
];

const ACCENT = {
  u1: { main: '#2F6F4E', soft: '#E4EEE7', text: '#1F4432' },
  u2: { main: '#3B5B8C', soft: '#E4E9F2', text: '#233A5C' },
};

function accentFor(id) {
  return ACCENT[id] || { main: '#6B7770', soft: '#ECEEEC', text: '#3A423D' };
}

function uid() {
  return Math.random().toString(36).slice(2, 9);
}
function todayStr() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60000);
  return local.toISOString().slice(0, 10);
}
function fmtDate(iso) {
  const dt = new Date(iso + 'T00:00:00');
  return `${dt.getMonth() + 1}/${dt.getDate()}`;
}
function fmtDateLong(iso) {
  const dt = new Date(iso + 'T00:00:00');
  const wd = ['日', '一', '二', '三', '四', '五', '六'][dt.getDay()];
  return `${dt.getMonth() + 1}月${dt.getDate()}日（週${wd}）`;
}

const FOOD_ANALYSIS_PROMPT = `你是營養估算助手。請仔細觀察這張食物照片，盡量辨識出照片中「每一樣」食物或飲料，並針對每一項估算其熱量與三大營養素。

只能回傳一個 JSON 物件，不要有任何其他文字、說明或 Markdown 符號（不要加反引號），格式如下：
{"items":[{"name":"食物名稱（繁體中文，簡短）","portion":"估計份量，例如 一碗、約200克","calories":數字(kcal),"protein":數字(公克),"fat":數字(公克),"carbs":數字(公克)}],"confidence":"high、medium 或 low 其中之一"}

如果照片中看不出明顯食物，items 請回傳空陣列。所有數字欄位都必須是數字，不要加單位文字。`;

async function analyzeFoodPhoto(base64Data, mediaType) {
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'claude-sonnet-4-6',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            { type: 'image', source: { type: 'base64', media_type: mediaType, data: base64Data } },
            { type: 'text', text: FOOD_ANALYSIS_PROMPT },
          ],
        },
      ],
    }),
  });
  if (!response.ok) throw new Error('API 請求失敗');
  const data = await response.json();
  const text = (data.content || [])
    .map((b) => (b.type === 'text' ? b.text : ''))
    .filter(Boolean)
    .join('\n');
  const cleaned = text.replace(/```json|```/g, '').trim();
  const parsed = JSON.parse(cleaned);
  if (!parsed || !Array.isArray(parsed.items)) throw new Error('回傳格式錯誤');
  return parsed;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () => reject(new Error('讀取圖片失敗'));
    reader.readAsDataURL(file);
  });
}

function normalizeEntry(e) {
  if (e.foods) return e;
  const foods =
    e.calorieIntake != null
      ? [{ id: uid(), name: '飲食攝取', portion: '', calories: e.calorieIntake, protein: 0, fat: 0, carbs: 0 }]
      : [];
  return { ...e, foods };
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [storageOk, setStorageOk] = useState(true);
  const [profile, setProfile] = useState({ users: DEFAULT_USERS });
  const [activeUser, setActiveUser] = useState('u1');
  const [logs, setLogs] = useState({ u1: [], u2: [] });
  const [tab, setTab] = useState('log');
  const [editingName, setEditingName] = useState(null);
  const [tempName, setTempName] = useState('');
  const [saveStatus, setSaveStatus] = useState('');
  const formTopRef = useRef(null);
  const fileInputRef = useRef(null);

  const [date, setDate] = useState(todayStr());
  const [weight, setWeight] = useState('');
  const [foods, setFoods] = useState([]);
  const [exercises, setExercises] = useState([{ name: '', calories: '' }]);
  const [isEditingExisting, setIsEditingExisting] = useState(false);

  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoError, setPhotoError] = useState('');

  // InBody (every 1-2 months) — separate from the daily log
  const [inbody, setInbody] = useState({ u1: [], u2: [] });
  const [ibDate, setIbDate] = useState(todayStr());
  const [ibWeight, setIbWeight] = useState('');
  const [ibBodyFat, setIbBodyFat] = useState('');
  const [ibMuscle, setIbMuscle] = useState('');
  const [ibVisceralFat, setIbVisceralFat] = useState('');
  const [ibBmr, setIbBmr] = useState('');
  const [ibSaveStatus, setIbSaveStatus] = useState('');

  useEffect(() => {
    init();
    // eslint-disable-next-line
  }, []);

  async function init() {
    let prof = { users: DEFAULT_USERS };
    try {
      const r = await window.storage.get('profile', false);
      if (r && r.value) prof = JSON.parse(r.value);
    } catch (e) {
      /* no saved profile yet */
    }
    setProfile(prof);

    const newLogs = {};
    const newInbody = {};
    for (const u of prof.users) {
      try {
        const r = await window.storage.get('log:' + u.id, false);
        const arr = r && r.value ? JSON.parse(r.value) : [];
        newLogs[u.id] = arr.map(normalizeEntry);
      } catch (e) {
        newLogs[u.id] = [];
      }

      try {
        const rIb = await window.storage.get('inbody:' + u.id, false);
        newInbody[u.id] = rIb && rIb.value ? JSON.parse(rIb.value) : [];
      } catch (e) {
        newInbody[u.id] = [];
      }
    }
    setLogs(newLogs);
    setInbody(newInbody);
    setLoading(false);
  }

  async function persistProfile(next) {
    setProfile(next);
    try {
      await window.storage.set('profile', JSON.stringify(next), false);
    } catch (e) {
      setStorageOk(false);
    }
  }

  async function persistLog(userId, entries) {
    setLogs((prev) => ({ ...prev, [userId]: entries }));
    try {
      await window.storage.set('log:' + userId, JSON.stringify(entries), false);
      setStorageOk(true);
    } catch (e) {
      setStorageOk(false);
    }
  }

  async function persistInbody(userId, entries) {
    setInbody((prev) => ({ ...prev, [userId]: entries }));
    try {
      await window.storage.set('inbody:' + userId, JSON.stringify(entries), false);
      setStorageOk(true);
    } catch (e) {
      setStorageOk(false);
    }
  }

  function resetForm(d) {
    setDate(d || todayStr());
    setWeight('');
    setFoods([]);
    setExercises([{ name: '', calories: '' }]);
    setIsEditingExisting(false);
  }

  function loadDate(d) {
    setDate(d);
    setPhotoError('');
    setPhotoPreview(null);
    const entries = logs[activeUser] || [];
    const existing = entries.find((e) => e.date === d);
    if (existing) {
      setWeight(existing.weight ?? '');
      setFoods((existing.foods || []).map((f) => ({ ...f })));
      setExercises(
        existing.exercises && existing.exercises.length
          ? existing.exercises.map((x) => ({ ...x, calories: String(x.calories) }))
          : [{ name: '', calories: '' }]
      );
      setIsEditingExisting(true);
    } else {
      setWeight('');
      setFoods([]);
      setExercises([{ name: '', calories: '' }]);
      setIsEditingExisting(false);
    }
  }

  useEffect(() => {
    loadDate(date);
    // eslint-disable-next-line
  }, [activeUser]);

  function updateExercise(idx, field, value) {
    setExercises((prev) => prev.map((ex, i) => (i === idx ? { ...ex, [field]: value } : ex)));
  }
  function addExercise() {
    setExercises((prev) => [...prev, { name: '', calories: '' }]);
  }
  function removeExercise(idx) {
    setExercises((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev));
  }

  function addFoodManual() {
    setFoods((prev) => [...prev, { id: uid(), name: '', portion: '', calories: '', protein: '', fat: '', carbs: '', estimated: false }]);
  }
  function updateFood(id, field, value) {
    setFoods((prev) => prev.map((f) => (f.id === id ? { ...f, [field]: value } : f)));
  }
  function removeFood(id) {
    setFoods((prev) => prev.filter((f) => f.id !== id));
  }

  async function handlePhotoChange(ev) {
    const file = ev.target.files && ev.target.files[0];
    ev.target.value = '';
    if (!file) return;
    setPhotoError('');
    setPhotoBusy(true);
    try {
      const previewUrl = URL.createObjectURL(file);
      setPhotoPreview(previewUrl);
      const base64 = await fileToBase64(file);
      const mediaType = file.type || 'image/jpeg';
      const result = await analyzeFoodPhoto(base64, mediaType);
      if (result.items.length === 0) {
        setPhotoError('沒有辨識出食物，請換一張照片或手動輸入。');
      } else {
        const newFoods = result.items.map((it) => ({
          id: uid(),
          name: it.name || '未命名食物',
          portion: it.portion || '',
          calories: Math.round(Number(it.calories) || 0),
          protein: Math.round(Number(it.protein) || 0),
          fat: Math.round(Number(it.fat) || 0),
          carbs: Math.round(Number(it.carbs) || 0),
          estimated: true,
        }));
        setFoods((prev) => [...prev, ...newFoods]);
      }
    } catch (e) {
      setPhotoError('辨識失敗，請確認網路連線後再試一次，或手動輸入。');
    } finally {
      setPhotoBusy(false);
    }
  }

  const liveBurned = useMemo(
    () => exercises.reduce((s, e) => s + (Number(e.calories) || 0), 0),
    [exercises]
  );
  const liveIntake = useMemo(() => foods.reduce((s, f) => s + (Number(f.calories) || 0), 0), [foods]);
  const liveMacros = useMemo(
    () =>
      foods.reduce(
        (m, f) => ({
          protein: m.protein + (Number(f.protein) || 0),
          fat: m.fat + (Number(f.fat) || 0),
          carbs: m.carbs + (Number(f.carbs) || 0),
        }),
        { protein: 0, fat: 0, carbs: 0 }
      ),
    [foods]
  );

  async function handleSave() {
    const entries = [...(logs[activeUser] || [])];
    const cleanFoods = foods
      .filter((f) => f.name.trim() || f.calories !== '')
      .map((f) => ({
        id: f.id || uid(),
        name: f.name.trim() || '未命名食物',
        portion: f.portion || '',
        calories: Number(f.calories) || 0,
        protein: Number(f.protein) || 0,
        fat: Number(f.fat) || 0,
        carbs: Number(f.carbs) || 0,
        estimated: !!f.estimated,
      }));
    const cleanExercises = exercises
      .filter((e) => e.name.trim() || e.calories !== '')
      .map((e) => ({ name: e.name.trim() || '未命名運動', calories: Number(e.calories) || 0 }));
    const totalBurned = cleanExercises.reduce((s, e) => s + e.calories, 0);
    const totalIntake = cleanFoods.reduce((s, f) => s + f.calories, 0);
    const idx = entries.findIndex((e) => e.date === date);
    const entry = {
      id: idx >= 0 ? entries[idx].id : uid(),
      date,
      weight: weight === '' ? null : Number(weight),
      foods: cleanFoods,
      calorieIntake: totalIntake,
      exercises: cleanExercises,
      totalBurned,
    };
    if (idx >= 0) entries[idx] = entry;
    else entries.push(entry);
    entries.sort((a, b) => a.date.localeCompare(b.date));
    await persistLog(activeUser, entries);
    setIsEditingExisting(true);
    setSaveStatus(storageOk ? '已儲存這天的紀錄' : '儲存失敗，請稍後再試');
    setTimeout(() => setSaveStatus(''), 1800);
  }

  async function handleDelete(entryId) {
    const entries = (logs[activeUser] || []).filter((e) => e.id !== entryId);
    await persistLog(activeUser, entries);
    if (entries.every((e) => e.date !== date)) resetForm(date);
  }

  async function handleSaveInbody() {
    const list = [...(inbody[activeUser] || [])];
    const item = {
      id: uid(),
      date: ibDate,
      weight: ibWeight === '' ? null : Number(ibWeight),
      bodyFat: ibBodyFat === '' ? null : Number(ibBodyFat),
      muscle: ibMuscle === '' ? null : Number(ibMuscle),
      visceralFat: ibVisceralFat === '' ? null : Number(ibVisceralFat),
      bmr: ibBmr === '' ? null : Number(ibBmr),
    };
    list.push(item);
    list.sort((a, b) => a.date.localeCompare(b.date));
    await persistInbody(activeUser, list);
    setIbSaveStatus('已儲存 InBody 紀錄');
    setIbWeight('');
    setIbBodyFat('');
    setIbMuscle('');
    setIbVisceralFat('');
    setIbBmr('');
    setTimeout(() => setIbSaveStatus(''), 1800);
  }

  async function handleDeleteInbody(id) {
    const list = (inbody[activeUser] || []).filter((item) => item.id !== id);
    await persistInbody(activeUser, list);
  }

  function startEditName(u) {
    setEditingName(u.id);
    setTempName(u.name);
  }
  async function saveEditName(u) {
    const next = {
      ...profile,
      users: profile.users.map((x) => (x.id === u.id ? { ...x, name: tempName.trim() || x.name } : x)),
    };
    await persistProfile(next);
    setEditingName(null);
  }

  const currentUser = profile.users.find((u) => u.id === activeUser) || profile.users[0];
  const accent = accentFor(activeUser);

  const sortedEntries = useMemo(
    () => [...(logs[activeUser] || [])].sort((a, b) => b.date.localeCompare(a.date)),
    [logs, activeUser]
  );

  const sortedInbody = useMemo(
    () => [...(inbody[activeUser] || [])].sort((a, b) => b.date.localeCompare(a.date)),
    [inbody, activeUser]
  );

  const chartData = useMemo(
    () =>
      [...(logs[activeUser] || [])]
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((e) => ({
          date: fmtDate(e.date),
          體重: e.weight,
          攝取熱量: e.calorieIntake,
          消耗熱量: e.totalBurned || 0,
        })),
    [logs, activeUser]
  );

  const hasWeightData = chartData.some((d) => d.體重 != null);
  const hasCalorieData = chartData.some((d) => d.攝取熱量 != null || d.消耗熱量);

  if (loading) {
    return (
      <div style={styles.loadingWrap}>
        <FontLoader />
        <div style={{ color: '#6B7770', fontFamily: 'Inter, sans-serif' }}>載入紀錄中…</div>
      </div>
    );
  }

  return (
    <div style={styles.app}>
      <FontLoader />

      <header style={styles.header}>
        <div style={styles.eyebrow}>DAILY LOG · 雙人紀錄本</div>
        <h1 style={styles.title}>體重與熱量追蹤</h1>
      </header>

      {/* User switcher */}
      <div style={styles.userSwitch}>
        {profile.users.map((u) => {
          const a = accentFor(u.id);
          const active = u.id === activeUser;
          const last = (logs[u.id] || []).slice().sort((x, y) => y.date.localeCompare(x.date))[0];
          return (
            <button
              key={u.id}
              onClick={() => setActiveUser(u.id)}
              style={{
                ...styles.userTab,
                borderColor: active ? a.main : '#D8DED6',
                background: active ? a.soft : '#FFFFFF',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 999,
                    background: a.main,
                    display: 'inline-block',
                    flexShrink: 0,
                  }}
                />
                {editingName === u.id ? (
                  <input
                    autoFocus
                    value={tempName}
                    onChange={(e) => setTempName(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.key === 'Enter' && saveEditName(u)}
                    style={styles.nameInput}
                  />
                ) : (
                  <span style={{ fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: 15, color: a.text }}>
                    {u.name}
                  </span>
                )}
                {editingName === u.id ? (
                  <Check
                    size={14}
                    onClick={(e) => {
                      e.stopPropagation();
                      saveEditName(u);
                    }}
                    color={a.text}
                  />
                ) : (
                  <Pencil
                    size={12}
                    onClick={(e) => {
                      e.stopPropagation();
                      startEditName(u);
                    }}
                    color="#9AA39C"
                  />
                )}
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#6B7770', marginTop: 4 }}>
                {last && last.weight != null ? `${last.weight} kg · ${fmtDate(last.date)}` : '尚無紀錄'}
              </div>
            </button>
          );
        })}
      </div>

      {/* Segmented control */}
      <div style={styles.segment}>
        <button
          onClick={() => setTab('log')}
          style={{ ...styles.segmentBtn, ...(tab === 'log' ? { background: accent.main, color: '#fff' } : {}) }}
        >
          <NotebookPen size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
          紀錄
        </button>
        <button
          onClick={() => setTab('trend')}
          style={{ ...styles.segmentBtn, ...(tab === 'trend' ? { background: accent.main, color: '#fff' } : {}) }}
        >
          <TrendingUp size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
          趨勢
        </button>
        <button
          onClick={() => setTab('inbody')}
          style={{ ...styles.segmentBtn, ...(tab === 'inbody' ? { background: accent.main, color: '#fff' } : {}) }}
        >
          <UserCheck size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
          InBody
        </button>
      </div>

      {tab === 'log' && (
        <div ref={formTopRef}>
          {/* Form card */}
          <div style={styles.card}>
            <div style={styles.cardHeaderRow}>
              <span style={{ ...styles.cardTitle }}>{fmtDateLong(date)}</span>
              {isEditingExisting && <span style={styles.editingBadge}>編輯既有紀錄</span>}
            </div>

            <label style={styles.label}>日期</label>
            <input type="date" value={date} onChange={(e) => loadDate(e.target.value)} style={styles.input} />

            <label style={styles.label}>
              <Scale size={13} style={styles.labelIcon} /> 體重 (kg)
            </label>
            <input
              type="number"
              inputMode="decimal"
              step="0.1"
              placeholder="例如 62.5"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              style={styles.input}
            />

            <div style={styles.divider} />

            <div style={styles.sectionHeadRow}>
              <label style={{ ...styles.label, marginTop: 0 }}>
                <Flame size={13} style={styles.labelIcon} /> 飲食紀錄
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                style={{ display: 'none' }}
                onChange={handlePhotoChange}
              />
              <button
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                disabled={photoBusy}
                style={{ ...styles.photoBtn, borderColor: accent.main, color: accent.text }}
              >
                {photoBusy ? (
                  <Loader2 size={14} className="spin" style={{ marginRight: 5, verticalAlign: -2 }} />
                ) : (
                  <Camera size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
                )}
                {photoBusy ? '辨識中…' : '拍照辨識'}
              </button>
            </div>

            {photoPreview && (
              <div style={styles.photoPreviewRow}>
                <img src={photoPreview} alt="上傳的食物照片" style={styles.photoThumb} />
                <span style={{ fontSize: 11, color: '#9AA39C', flex: 1 }}>
                  {photoBusy ? '正在估算熱量與營養素…' : '辨識完成，結果已加到下方清單，請確認後再儲存'}
                </span>
                <X
                  size={14}
                  color="#9AA39C"
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setPhotoPreview(null);
                    setPhotoError('');
                  }}
                />
              </div>
            )}
            {photoError && <div style={styles.photoError}>{photoError}</div>}

            {foods.length === 0 && <div style={styles.emptyState}>還沒有飲食項目，拍照辨識或手動新增一筆吧。</div>}

            {foods.map((f) => (
              <div key={f.id} style={styles.foodCard}>
                <div style={styles.exRow}>
                  <input
                    placeholder="食物名稱"
                    value={f.name}
                    onChange={(e) => updateFood(f.id, 'name', e.target.value)}
                    style={{ ...styles.input, flex: 1.6, marginBottom: 0 }}
                  />
                  <input
                    type="number"
                    inputMode="numeric"
                    placeholder="kcal"
                    value={f.calories}
                    onChange={(e) => updateFood(f.id, 'calories', e.target.value)}
                    style={{ ...styles.input, flex: 0.8, marginBottom: 0 }}
                  />
                  <button onClick={() => removeFood(f.id)} style={styles.iconBtn} aria-label="刪除此項飲食">
                    <Trash2 size={15} color="#9AA39C" />
                  </button>
                </div>
                <div style={styles.macroRow}>
                  {f.estimated && (
                    <span style={styles.aiTag}>
                      <Sparkles size={10} style={{ verticalAlign: -1, marginRight: 2 }} />
                      AI 估算
                    </span>
                  )}
                  {f.portion && <span style={styles.portionTag}>{f.portion}</span>}
                  <span style={styles.macroInputWrap}>
                    蛋白
                    <input
                      type="number"
                      value={f.protein}
                      onChange={(e) => updateFood(f.id, 'protein', e.target.value)}
                      style={styles.macroInput}
                    />
                    g
                  </span>
                  <span style={styles.macroInputWrap}>
                    脂肪
                    <input
                      type="number"
                      value={f.fat}
                      onChange={(e) => updateFood(f.id, 'fat', e.target.value)}
                      style={styles.macroInput}
                    />
                    g
                  </span>
                  <span style={styles.macroInputWrap}>
                    碳水
                    <input
                      type="number"
                      value={f.carbs}
                      onChange={(e) => updateFood(f.id, 'carbs', e.target.value)}
                      style={styles.macroInput}
                    />
                    g
                  </span>
                </div>
              </div>
            ))}
            <button onClick={addFoodManual} style={{ ...styles.ghostBtn, borderColor: accent.main, color: accent.text }}>
              <Plus size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
              手動新增飲食項目
            </button>

            <div style={styles.summaryLine}>
              今日飲食共 <b style={{ color: accent.text }}>{liveIntake}</b> kcal
              {(liveMacros.protein || liveMacros.fat || liveMacros.carbs) > 0 && (
                <span style={{ color: '#9AA39C' }}>
                  {' '}
                  （蛋白 {liveMacros.protein}g · 脂肪 {liveMacros.fat}g · 碳水 {liveMacros.carbs}g）
                </span>
              )}
            </div>

            <div style={styles.divider} />

            <label style={{ ...styles.label, marginTop: 0 }}>
              <Dumbbell size={13} style={styles.labelIcon} /> 運動項目與消耗熱量
            </label>
            {exercises.map((ex, idx) => (
              <div key={idx} style={styles.exRow}>
                <input
                  placeholder="運動名稱，例如慢跑"
                  value={ex.name}
                  onChange={(e) => updateExercise(idx, 'name', e.target.value)}
                  style={{ ...styles.input, flex: 1.4, marginBottom: 0 }}
                />
                <input
                  type="number"
                  inputMode="numeric"
                  placeholder="kcal"
                  value={ex.calories}
                  onChange={(e) => updateExercise(idx, 'calories', e.target.value)}
                  style={{ ...styles.input, flex: 0.8, marginBottom: 0 }}
                />
                <button onClick={() => removeExercise(idx)} style={styles.iconBtn} aria-label="刪除此項運動">
                  <Trash2 size={15} color="#9AA39C" />
                </button>
              </div>
            ))}
            <button onClick={addExercise} style={{ ...styles.ghostBtn, borderColor: accent.main, color: accent.text }}>
              <Plus size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
              新增運動項目
            </button>

            <div style={styles.summaryLine}>
              今日運動共消耗 <b style={{ color: accent.text }}>{liveBurned}</b> kcal
            </div>

            <button onClick={handleSave} style={{ ...styles.saveBtn, background: accent.main }}>
              儲存這天的紀錄
            </button>
            {saveStatus && <div style={styles.saveStatus}>{saveStatus}</div>}
          </div>

          {/* History ledger */}
          <div style={styles.historyHeader}>
            <span style={styles.historyTitle}>歷程</span>
            <span style={styles.historyCount}>{sortedEntries.length} 筆</span>
          </div>

          {sortedEntries.length === 0 && (
            <div style={styles.emptyState}>還沒有任何紀錄，填寫上方表單開始追蹤吧。</div>
          )}

          {sortedEntries.map((e, i) => (
            <div
              key={e.id}
              onClick={() => {
                loadDate(e.date);
                if (formTopRef.current) formTopRef.current.scrollIntoView({ behavior: 'smooth' });
              }}
              style={{ ...styles.ledgerRow, borderLeftColor: e.date === date ? accent.main : '#D8DED6' }}
            >
              <span style={styles.ledgerIndex}>{String(sortedEntries.length - i).padStart(3, '0')}</span>
              <div style={{ flex: 1 }}>
                <div style={styles.ledgerDate}>{fmtDateLong(e.date)}</div>
                <div style={styles.ledgerStats}>
                  {e.weight != null && <span>{e.weight} kg</span>}
                  {e.calorieIntake > 0 && <span>攝取 {e.calorieIntake} kcal</span>}
                  {e.totalBurned > 0 && <span>消耗 {e.totalBurned} kcal</span>}
                  {e.foods && e.foods.length > 0 && (
                    <span style={{ color: '#9AA39C' }}>{e.foods.map((x) => x.name).join('、')}</span>
                  )}
                </div>
              </div>
              <ChevronRight size={14} color="#C7CEC7" style={{ marginRight: 6 }} />
              <button
                onClick={(ev) => {
                  ev.stopPropagation();
                  handleDelete(e.id);
                }}
                style={styles.iconBtn}
                aria-label="刪除這筆紀錄"
              >
                <Trash2 size={14} color="#C7A5A0" />
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === 'trend' && (
        <div>
          <div style={styles.card}>
            <div style={styles.cardTitle}>體重變化</div>
            {!hasWeightData ? (
              <div style={styles.emptyState}>尚無體重資料，先在「紀錄」頁新增幾天的體重吧。</div>
            ) : (
              <div style={{ width: '100%', height: 220 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="#E4E9E4" strokeDasharray="4 4" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7770' }} axisLine={{ stroke: '#D8DED6' }} tickLine={false} />
                    <YAxis
                      domain={['dataMin - 1', 'dataMax + 1']}
                      tick={{ fontSize: 11, fill: '#6B7770' }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                    />
                    <Tooltip contentStyle={{ fontSize: 12, fontFamily: 'Inter, sans-serif', borderRadius: 8 }} />
                    <Line type="monotone" dataKey="體重" stroke={accent.main} strokeWidth={2.5} dot={{ r: 3, fill: accent.main }} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div style={styles.card}>
            <div style={styles.cardTitle}>熱量攝取與消耗</div>
            {!hasCalorieData ? (
              <div style={styles.emptyState}>尚無熱量資料，先在「紀錄」頁新增飲食或運動紀錄吧。</div>
            ) : (
              <div style={{ width: '100%', height: 220 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke="#E4E9E4" strokeDasharray="4 4" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7770' }} axisLine={{ stroke: '#D8DED6' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#6B7770' }} axisLine={false} tickLine={false} width={40} />
                    <Tooltip contentStyle={{ fontSize: 12, fontFamily: 'Inter, sans-serif', borderRadius: 8 }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="攝取熱量" fill="#D9B26A" radius={[4, 4, 0, 0]} barSize={14} />
                    <Line type="monotone" dataKey="消耗熱量" stroke={accent.main} strokeWidth={2.5} dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'inbody' && (
        <div>
          <div style={styles.card}>
            <div style={styles.cardTitle}>新增 InBody 身體組成紀錄</div>

            <label style={styles.label}>量測日期</label>
            <input type="date" value={ibDate} onChange={(e) => setIbDate(e.target.value)} style={styles.input} />

            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>體重 (kg)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  placeholder="62.5"
                  value={ibWeight}
                  onChange={(e) => setIbWeight(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>體脂率 (%)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  placeholder="20.5"
                  value={ibBodyFat}
                  onChange={(e) => setIbBodyFat(e.target.value)}
                  style={styles.input}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>骨骼肌重 (kg)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  placeholder="28.0"
                  value={ibMuscle}
                  onChange={(e) => setIbMuscle(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>內臟脂肪等級</label>
                <input
                  type="number"
                  inputMode="numeric"
                  placeholder="5"
                  value={ibVisceralFat}
                  onChange={(e) => setIbVisceralFat(e.target.value)}
                  style={styles.input}
                />
              </div>
            </div>

            <label style={styles.label}>基礎代謝率 BMR (kcal)</label>
            <input
              type="number"
              inputMode="numeric"
              placeholder="1450"
              value={ibBmr}
              onChange={(e) => setIbBmr(e.target.value)}
              style={styles.input}
            />

            <button onClick={handleSaveInbody} style={{ ...styles.saveBtn, background: accent.main, marginTop: 10 }}>
              儲存 InBody 紀錄
            </button>
            {ibSaveStatus && <div style={styles.saveStatus}>{ibSaveStatus}</div>}
          </div>

          <div style={styles.historyHeader}>
            <span style={styles.historyTitle}>InBody 歷史紀錄</span>
            <span style={styles.historyCount}>{sortedInbody.length} 筆</span>
          </div>

          {sortedInbody.length === 0 && (
            <div style={styles.emptyState}>尚無 InBody 紀錄，定期量測後可在此建檔。</div>
          )}

          {sortedInbody.map((item, i) => (
            <div key={item.id} style={{ ...styles.ledgerRow, borderLeftColor: accent.main }}>
              <span style={styles.ledgerIndex}>{String(sortedInbody.length - i).padStart(3, '0')}</span>
              <div style={{ flex: 1 }}>
                <div style={styles.ledgerDate}>{fmtDateLong(item.date)}</div>
                <div style={styles.ledgerStats}>
                  {item.weight != null && <span>體重 {item.weight} kg</span>}
                  {item.bodyFat != null && <span>體脂 {item.bodyFat}%</span>}
                  {item.muscle != null && <span>骨骼肌 {item.muscle} kg</span>}
                  {item.visceralFat != null && <span>內臟脂肪 {item.visceralFat}</span>}
                  {item.bmr != null && <span style={{ color: accent.main, fontWeight: 600 }}>BMR {item.bmr} kcal</span>}
                </div>
              </div>
              <button
                onClick={() => handleDeleteInbody(item.id)}
                style={styles.iconBtn}
                aria-label="刪除這筆 InBody 紀錄"
              >
                <Trash2 size={14} color="#C7A5A0" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div style={styles.footNote}>
        資料只儲存在你目前使用的帳號中，切換裝置或帳號將看不到這些紀錄。拍照估算的熱量與營養素僅供參考，實際數值可能有落差，建議於儲存前手動核對。
      </div>
    </div>
  );
}

function FontLoader() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
      .spin { animation: spin 1s linear infinite; }
      @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    `}</style>
  );
}

const styles = {
  app: {
    fontFamily: "'Inter', sans-serif",
    background: '#EEF1EC',
    minHeight: '100%',
    padding: '20px 14px 40px',
    maxWidth: 480,
    margin: '0 auto',
    color: '#1F2A24',
    boxSizing: 'border-box',
  },
  loadingWrap: { display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 },
  header: { marginBottom: 16, paddingLeft: 2 },
  eyebrow: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: '0.08em', color: '#6B7770', marginBottom: 4 },
  title: { fontFamily: "'Fraunces', serif", fontSize: 26, fontWeight: 700, margin: 0, color: '#1F2A24' },
  userSwitch: { display: 'flex', gap: 8, marginBottom: 12 },
  userTab: { flex: 1, border: '1.5px solid #D8DED6', borderRadius: 12, padding: '10px 12px', textAlign: 'left', cursor: 'pointer', transition: 'all 0.15s' },
  nameInput: { fontFamily: "'Fraunces', serif", fontSize: 14, fontWeight: 600, border: 'none', borderBottom: '1px solid #9AA39C', background: 'transparent', width: 70, outline: 'none', padding: 0 },
  segment: { display: 'flex', background: '#E1E6DF', borderRadius: 10, padding: 3, marginBottom: 16 },
  segmentBtn: { flex: 1, border: 'none', background: 'transparent', padding: '9px 0', borderRadius: 8, fontSize: 12, fontWeight: 600, fontFamily: "'Inter', sans-serif", color: '#4A544D', cursor: 'pointer' },
  card: { background: '#FFFFFF', border: '1px solid #E2E7E1', borderRadius: 16, padding: 16, marginBottom: 16 },
  cardHeaderRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  cardTitle: { fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: 16, marginBottom: 10 },
  editingBadge: { fontSize: 10, color: '#9A7B3F', background: '#FBF1DD', padding: '2px 8px', borderRadius: 999, fontFamily: "'IBM Plex Mono', monospace" },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#4A544D', marginBottom: 6, marginTop: 10 },
  labelIcon: { verticalAlign: -2, marginRight: 3 },
  input: { width: '100%', border: '1px solid #D8DED6', borderRadius: 9, padding: '9px 10px', fontSize: 14, fontFamily: "'Inter', sans-serif", marginBottom: 4, boxSizing: 'border-box', outline: 'none', background: '#FBFCFB' },
  divider: { borderTop: '1px dashed #D8DED6', margin: '14px 0 4px' },
  sectionHeadRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  photoBtn: { border: '1.3px solid', background: '#fff', borderRadius: 9, padding: '6px 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer' },
  photoPreviewRow: { display: 'flex', alignItems: 'center', gap: 8, background: '#F7F8F6', border: '1px solid #E2E7E1', borderRadius: 10, padding: 8, marginBottom: 10 },
  photoThumb: { width: 40, height: 40, objectFit: 'cover', borderRadius: 8, flexShrink: 0 },
  photoError: { fontSize: 12, color: '#B8654F', background: '#FCEEEA', borderRadius: 8, padding: '6px 10px', marginBottom: 10 },
  foodCard: { background: '#FBFCFB', border: '1px solid #ECEFEA', borderRadius: 10, padding: '8px 8px 10px', marginBottom: 8 },
  exRow: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 },
  macroRow: { display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', paddingLeft: 2 },
  aiTag: { fontSize: 10, color: '#9A7B3F', background: '#FBF1DD', padding: '2px 6px', borderRadius: 999, fontFamily: "'IBM Plex Mono', monospace" },
  portionTag: { fontSize: 10, color: '#6B7770', background: '#EEF1EC', padding: '2px 6px', borderRadius: 999 },
  macroInputWrap: { fontSize: 11, color: '#6B7770', display: 'flex', alignItems: 'center', gap: 3 },
  macroInput: { width: 34, border: '1px solid #D8DED6', borderRadius: 6, padding: '2px 4px', fontSize: 11, textAlign: 'center', outline: 'none' },
  iconBtn: { border: 'none', background: 'transparent', cursor: 'pointer', padding: 6, display: 'flex', alignItems: 'center' },
  ghostBtn: { border: '1.3px dashed', background: 'transparent', borderRadius: 9, padding: '8px 12px', fontSize: 13, fontWeight: 600, cursor: 'pointer', marginTop: 2 },
  summaryLine: { fontSize: 13, color: '#4A544D', marginTop: 14, marginBottom: 10 },
  saveBtn: { width: '100%', border: 'none', color: '#fff', padding: '12px 0', borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: "'Inter', sans-serif" },
  saveStatus: { textAlign: 'center', fontSize: 12, color: '#4A544D', marginTop: 8 },
  historyHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', margin: '4px 4px 8px' },
  historyTitle: { fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: 15 },
  historyCount: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#9AA39C' },
  emptyState: { fontSize: 13, color: '#9AA39C', padding: '10px 2px' },
  ledgerRow: { display: 'flex', alignItems: 'center', background: '#FFFFFF', border: '1px solid #E2E7E1', borderLeft: '3px solid #D8DED6', borderRadius: 10, padding: '10px 10px', marginBottom: 8, cursor: 'pointer', gap: 8 },
  ledgerIndex: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#C7CEC7', width: 26, flexShrink: 0 },
  ledgerDate: { fontSize: 13, fontWeight: 600, marginBottom: 2 },
  ledgerStats: { display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 12, color: '#4A544D' },
  footNote: { textAlign: 'center', fontSize: 11, color: '#9AA39C', marginTop: 8, lineHeight: 1.5 },
};
