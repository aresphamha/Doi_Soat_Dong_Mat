/**
 * FMCG MATRIX ENGINE - Tab 8: Báo Cáo Logistics Kho Khô FMCG (CDC StarRocks + Seedlog)
 * - View 1: Bảng Ma Trận 53 chỉ số (đủ 6 khối + Tài chính 53-55) kèm cột TỔNG/LŨY KẾ và nút xem nhanh logic từng dòng (ⓘ)
 * - View 2: Đặc Tả Logic Chi Tiết (Phần A: Cột & Đồng bộ tự động, Phần B: 53 Hàng chỉ số) kèm nút Copy Markdown & Xuất Excel
 * - View 3: Bảng Đối Chiếu Kiểm Chứng CDC StarRocks (blank=0 & blank=-1) vs Google Sheet Seedlog
 */

(function () {
    let currentData = null;
    let sortDescending = true;
    let filterSection = 'all';
    let searchQuery = '';
    let activeSubView = 'matrix'; // 'matrix' | 'flow' | 'logic' | 'reconcile'
    let flowBlockFilter = 'all';  // 'all' | 'D0' | 'D1' | 'D2' | 'D3' | 'D4' | 'B1'
    let flowSummaryOnly = false;  // false = Ngày + Σ Tuần + Σ T11, true = Chỉ Σ T11 + Σ Tuần
    // Chế độ Ẩn/Hiện từng cột (Hide/Show Columns) cho Bảng 2 (113 Chỉ Số)
    let flowColsVis = {
        meta: false,  // A, B, C (Miền, Kho, Nhóm) — mặc định ẩn để thấy ngay cột số liệu
        unit: true,   // F (Đơn vị)
        src: true,    // G (Nguồn dữ liệu)
        logic: false, // H (Cách tính & Logic) — mặc định ẩn để thấy ngay Σ T11 & các ngày
    };
    let isFullscreen = false;
    let tableZoom = 100;          // 70 .. 130 (%)

    // Tiêm CSS tối ưu độ dễ đọc: kẻ lưới dọc/ngang rõ, nền cột xen kẽ, hover sáng nguyên hàng, tabular-nums
    (function injectFmcgGridCss() {
        if (document.getElementById('fmcg-grid-readability-css')) return;
        const st = document.createElement('style');
        st.id = 'fmcg-grid-readability-css';
        st.textContent = `
            .fmcg-readable-tbl { border-collapse: separate; border-spacing: 0; font-variant-numeric: tabular-nums; }
            .fmcg-readable-tbl tbody tr.fmcg-data-row:hover td {
                background: rgba(56, 189, 248, 0.14) !important;
                color: #ffffff;
            }
            .fmcg-readable-tbl tbody tr.fmcg-data-row:hover td.fmcg-sticky-col {
                background: #17304d !important;
            }
            .fmcg-readable-tbl td.fmcg-day-odd { background: rgba(255, 255, 255, 0.022); }
            .fmcg-readable-tbl th.fmcg-day-odd { background: #131f35 !important; }
            .fmcg-readable-tbl td.fmcg-num-td {
                padding: 0.56rem 0.9rem !important;
                border-right: 1px solid rgba(148, 163, 184, 0.17) !important;
                border-bottom: 1px solid rgba(148, 163, 184, 0.12) !important;
                letter-spacing: 0.01em;
            }
            .fmcg-readable-tbl th.fmcg-day-th {
                padding: 0.68rem 0.9rem !important;
                border-right: 1px solid rgba(148, 163, 184, 0.22) !important;
                border-bottom: 2px solid rgba(56, 189, 248, 0.35) !important;
            }
            /* Đồng bộ màu badge & text của 4 nút sub-tab chuẩn Tab 2 cho Bảng 5 FMCG */
            .fmcg-prog-wrap .sub-tab-btn.active-sub-1 .tab-badge-num { background: #38bdf8; color: #0f172a; font-weight: 900; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-1 .tab-btn-text { color: #38bdf8; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-2 .tab-badge-num { background: #34d399; color: #064e3b; font-weight: 900; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-2 .tab-btn-text { color: #34d399; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-3 .tab-badge-num { background: #fbbf24; color: #78350f; font-weight: 900; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-3 .tab-btn-text { color: #fbbf24; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-4 .tab-badge-num { background: #f87171; color: #450a0a; font-weight: 900; }
            .fmcg-prog-wrap .sub-tab-btn.active-sub-4 .tab-btn-text { color: #f87171; }
            .fmcg-prog-wrap .fmcg-st-toolbar input,
            .fmcg-prog-wrap .fmcg-st-toolbar select {
                background: var(--bg-card);
                color: var(--text-primary);
                border: 1px solid var(--border-card);
            }
        `;
        document.head.appendChild(st);
    })();

    // Phím ESC để thoát chế độ mở rộng toàn màn hình
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isFullscreen) {
            window.toggleFmcgFullscreen(false);
        }
    });

    window.toggleFmcgFullscreen = function (forceState) {
        isFullscreen = (typeof forceState === 'boolean') ? forceState : !isFullscreen;
        const wrap = document.getElementById('fmcg-table-container');
        const btn = document.getElementById('btn-fmcg-fullscreen');
        if (!wrap) return;

        if (isFullscreen) {
            wrap.style.position = 'fixed';
            wrap.style.inset = '0';
            wrap.style.width = '100vw';
            wrap.style.height = '100vh';
            wrap.style.maxHeight = '100vh';
            wrap.style.zIndex = '9998';
            wrap.style.borderRadius = '0';
            wrap.style.overflow = 'auto';
            wrap.style.background = '#0b1120';
            document.body.style.overflow = 'hidden';
        } else {
            const isProg = activeSubView === 'progress';
            wrap.style.position = '';
            wrap.style.inset = '';
            wrap.style.width = '';
            wrap.style.height = '';
            wrap.style.maxHeight = (activeSubView === 'matrix' || activeSubView === 'flow') ? '74vh' : 'none';
            wrap.style.zIndex = '';
            wrap.style.borderRadius = isProg ? '0' : '12px';
            wrap.style.border = isProg ? 'none' : '1px solid rgba(255,255,255,0.1)';
            wrap.style.boxShadow = isProg ? 'none' : '0 4px 16px rgba(0,0,0,0.22)';
            wrap.style.overflow = '';
            wrap.style.overflowX = (activeSubView === 'logic' || isProg) ? 'visible' : 'auto';
            wrap.style.background = isProg ? 'transparent' : '#1a2436';
            document.body.style.overflow = '';
        }

        if (btn) {
            btn.innerHTML = isFullscreen
                ? '<i class="fa-solid fa-compress"></i> Thu Nhỏ Bảng'
                : '<i class="fa-solid fa-expand"></i> Mở Rộng Bảng';
        }
        renderActiveSubView();
    };

    window.adjustFmcgZoom = function (delta) {
        if (delta === 0) {
            tableZoom = 100;
        } else {
            tableZoom = Math.min(130, Math.max(70, tableZoom + delta));
        }
        applyFmcgZoomAndBar();
    };

    function getFullscreenTopBarHtml() {
        if (!isFullscreen) return '';
        const views = [
            { id: 'matrix', label: '1. Đối Soát FMCG (53 Chỉ Số)', icon: 'fa-table' },
            { id: 'flow', label: '2. Đối Soát FMCG (113 Chỉ Số)', icon: 'fa-diagram-project' },
            { id: 'logic', label: '3. Logic Chi Tiết', icon: 'fa-book-open' },
            { id: 'reconcile', label: '4. Đối Chiếu CDC', icon: 'fa-circle-check' },
        ];
        return `
            <div id="fmcg-fs-topbar" style="position:sticky; top:0; left:0; z-index:40; background:#1a2436; border-bottom:1px solid rgba(56,189,248,0.25); padding:0.55rem 1rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.45rem; flex-wrap:wrap;">
                    <span style="color:#94a3b8; font-weight:500; font-size:0.78rem; margin-right:0.4rem;">
                        <i class="fa-solid fa-expand" style="margin-right:0.35rem;"></i> CHẾ ĐỘ XEM TOÀN MÀN HÌNH
                    </span>
                    ${views.map(v => {
            const act = activeSubView === v.id;
            return `<button onclick="switchFmcgSubView('${v.id}')" style="background:${act ? '#0369a1' : '#28354a'}; color:${act ? '#ffffff' : '#cbd5e1'}; border:1px solid ${act ? 'rgba(56,189,248,0.5)' : 'rgba(255,255,255,0.1)'}; border-radius:6px; padding:0.32rem 0.7rem; font-size:0.76rem; font-weight:700; cursor:pointer;"><i class="fa-solid ${v.icon}" style="margin-right:0.3rem;"></i>${v.label}</button>`;
        }).join('')}
                </div>
                <div style="display:flex; align-items:center; gap:0.45rem; flex-wrap:wrap;">
                    <div style="display:inline-flex; align-items:center; background:#1e293b; border:1px solid rgba(255,255,255,0.12); border-radius:6px; overflow:hidden;">
                        <button onclick="adjustFmcgZoom(-10)" title="Thu nhỏ chữ" style="background:transparent; color:#e2e8f0; border:none; padding:0.3rem 0.6rem; cursor:pointer; font-weight:800;">−</button>
                        <button onclick="adjustFmcgZoom(0)" title="Đặt lại 100%" id="fmcg-zoom-label" style="background:rgba(148,163,184,0.08); color:#cbd5e1; border:none; border-left:1px solid rgba(255,255,255,0.08); border-right:1px solid rgba(255,255,255,0.08); padding:0.3rem 0.55rem; cursor:pointer; font-size:0.74rem; font-weight:700; font-family:'JetBrains Mono', monospace;">${tableZoom}%</button>
                        <button onclick="adjustFmcgZoom(10)" title="Phóng to chữ" style="background:transparent; color:#e2e8f0; border:none; padding:0.3rem 0.6rem; cursor:pointer; font-weight:800;">+</button>
                    </div>
                    <button onclick="exportFmcgExcel()" style="background:#1c2433; color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:0.34rem 0.75rem; font-size:0.76rem; font-weight:700; cursor:pointer;">
                        <i class="fa-solid fa-file-excel"></i> Xuất Excel
                    </button>
                    <button onclick="exportFmcgPdf()" style="background:#1c2433; color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:0.34rem 0.75rem; font-size:0.76rem; font-weight:700; cursor:pointer;">
                        <i class="fa-solid fa-file-pdf"></i> Tải PDF
                    </button>
                    <button onclick="toggleFmcgFullscreen(false)" style="background:#262f40; color:#e2e8f0; border:1px solid rgba(255,255,255,0.14); border-radius:6px; padding:0.34rem 0.85rem; font-size:0.76rem; font-weight:800; cursor:pointer;">
                        ✕ Thu Nhỏ (ESC)
                    </button>
                </div>
            </div>
        `;
    }

    function applyFmcgZoomAndBar() {
        const wrap = document.getElementById('fmcg-table-container');
        if (!wrap) return;
        const inner = wrap.querySelector('.fmcg-zoom-target');
        if (inner) {
            inner.style.zoom = (tableZoom / 100);
        }
        const zLbl = document.getElementById('fmcg-zoom-label');
        if (zLbl) zLbl.textContent = tableZoom + '%';
        const zLblOut = document.getElementById('fmcg-zoom-label-out');
        if (zLblOut) zLblOut.textContent = tableZoom + '%';
    }

    window.renderFmcgMatrix = function () {
        if (!currentData && window.FMCG_MATRIX_DATA) {
            currentData = JSON.parse(JSON.stringify(window.FMCG_MATRIX_DATA));
        }
        buildUI();
    };

    function buildUI() {
        if (!currentData || !currentData.dates || currentData.dates.length === 0) {
            const tableWrap = document.getElementById('fmcg-table-container');
            if (tableWrap) {
                tableWrap.innerHTML = `
                    <div style="padding:3rem; text-align:center; color:#94a3b8;">
                        <i class="fa-solid fa-spinner fa-spin" style="font-size:2rem; color:#38bdf8; margin-bottom:1rem;"></i>
                        <p style="font-size:1rem; font-weight:600;">Đang chuẩn bị dữ liệu Báo cáo Logistics FMCG...</p>
                    </div>`;
            }
            return;
        }

        renderKPICards();
        renderActiveSubView();
    }

    window.switchFmcgSubView = function (viewName) {
        activeSubView = viewName;
        document.querySelectorAll('.fmcg-subview-btn').forEach(btn => {
            const isAct = btn.getAttribute('data-view') === viewName;
            btn.style.background = isAct ? 'linear-gradient(135deg, #0284c7, #0ea5e9)' : '#1e293b';
            btn.style.color = isAct ? '#fff' : '#94a3b8';
            btn.style.borderColor = isAct ? '#38bdf8' : 'rgba(255,255,255,0.1)';
            btn.style.boxShadow = isAct ? '0 0 12px rgba(56,189,248,0.3)' : 'none';
        });

        const secBar = document.getElementById('fmcg-filter-bar');
        if (secBar) {
            secBar.style.display = (viewName === 'reconcile' || viewName === 'flow') ? 'none' : 'flex';
            secBar.style.display = (viewName === 'reconcile' || viewName === 'flow' || viewName === 'progress') ? 'none' : 'flex';
        }
        const tblWrap = document.getElementById('fmcg-table-container');
        if (tblWrap && !isFullscreen) {
            tblWrap.style.maxHeight = (viewName === 'matrix' || viewName === 'flow') ? '74vh' : 'none';
            const isProg = viewName === 'progress';
            tblWrap.style.maxHeight = (viewName === 'matrix' || viewName === 'flow') ? '74vh' : 'none';
            tblWrap.style.overflowX = (viewName === 'logic' || isProg) ? 'visible' : 'auto';
            tblWrap.style.background = isProg ? 'transparent' : '#1a2436';
            tblWrap.style.border = isProg ? 'none' : '1px solid rgba(255,255,255,0.1)';
            tblWrap.style.boxShadow = isProg ? 'none' : '0 4px 16px rgba(0,0,0,0.22)';
            tblWrap.style.borderRadius = isProg ? '0' : '12px';
        }
        renderActiveSubView();
    };

    function renderActiveSubView() {
        if (activeSubView === 'flow') {
            renderFlowTemplateView();
        } else if (activeSubView === 'logic') {
            renderLogicView();
        } else if (activeSubView === 'reconcile') {
            renderReconcileView();
        } else if (activeSubView === 'progress') {
            renderProgressView();
        } else {
            renderMatrixTable();
        }
        // Bọc nội dung vào lớp zoom + chèn thanh Fullscreen Top Bar nếu đang mở rộng
        const wrap = document.getElementById('fmcg-table-container');
        if (wrap) {
            const contentHtml = wrap.innerHTML;
            wrap.innerHTML = getFullscreenTopBarHtml() + `<div class="fmcg-zoom-target" style="zoom:${tableZoom / 100};">${contentHtml}</div>`;
        }
        applyFmcgZoomAndBar();
    }

    window.setFmcgFlowBlock = function (blkId) {
        flowBlockFilter = blkId;
        renderActiveSubView();
    };

    window.toggleFmcgFlowSummaryOnly = function () {
        flowSummaryOnly = !flowSummaryOnly;
        renderActiveSubView();
    };

    window.toggleFmcgFlowCol = function (colKey) {
        if (colKey === 'all_on') {
            flowColsVis = { meta: true, unit: true, src: true, logic: true };
        } else if (colKey === 'compact') {
            flowColsVis = { meta: false, unit: true, src: false, logic: false };
        } else if (Object.prototype.hasOwnProperty.call(flowColsVis, colKey)) {
            flowColsVis[colKey] = !flowColsVis[colKey];
        }
        renderFlowTemplateView();
    };

    // Giữ tương thích ngược nếu có nơi nào gọi cũ
    window.toggleFmcgFlowMeta = function () { window.toggleFmcgFlowCol('meta'); };
    window.toggleFmcgFlowGH = function () {
        const next = !(flowColsVis.src && flowColsVis.logic);
        flowColsVis.src = next;
        flowColsVis.logic = next;
        renderFlowTemplateView();
    };

    // ==================== VIEW NEW: ĐỐI SOÁT FMCG (113 CHỈ SỐ · Đ0 -> Đ4 + B. TỒN ÂM) ====================
    function renderFlowTemplateView() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;

        const ft = currentData.flow_template;
        if (!ft || !ft.blocks || !ft.columns) {
            container.innerHTML = `<div style="padding:2.5rem; text-align:center; color:#94a3b8;">Chưa có dữ liệu Đối Soát FMCG (113 Chỉ Số). Hãy bấm <strong>Cập Nhật Realtime (CDC &amp; Seedlog)</strong> để nạp mới nhất!</div>`;
            return;
        }

        const monthCol = ft.columns.find(c => c.type === 'month') || ft.columns[0];
        let otherCols = ft.columns.filter(c => c.type !== 'month');
        if (flowSummaryOnly) {
            otherCols = otherCols.filter(c => c.type === 'week');
        }
        if (sortDescending) {
            const weeks = [];
            const byWeek = {};
            otherCols.forEach(c => {
                const wk = c.week || 'OTHER';
                if (!byWeek[wk]) { weeks.push(wk); byWeek[wk] = []; }
                byWeek[wk].push(c);
            });
            weeks.reverse();
            otherCols = [];
            weeks.forEach(wk => {
                const colsInWk = byWeek[wk];
                const wkSum = colsInWk.filter(c => c.type === 'week');
                const wkDays = colsInWk.filter(c => c.type === 'day').reverse();
                otherCols.push(...wkSum, ...wkDays);
            });
        }

        const totalAll = ft.blocks.reduce((s, b) => s + (b.rows ? b.rows.length : 0), 0);
        const countOf = (id) => {
            const b = ft.blocks.find(x => x.id === id);
            return b && b.rows ? b.rows.length : 0;
        };

        const blockPills = [
            { id: 'all', label: `Tất cả (${totalAll})` },
            { id: 'D0', label: `Đ0 (${countOf('D0')})` },
            { id: 'D1', label: `Đ1 (${countOf('D1')})` },
            { id: 'D2', label: `Đ2 (${countOf('D2')})` },
            { id: 'D3', label: `Đ3 (${countOf('D3')})` },
            { id: 'D4', label: `Đ4 (${countOf('D4')})` },
            { id: 'B1', label: `B. Tồn âm (${countOf('B1')})` },
        ];

        const srcBadgeStyle = (s) => {
            const low = String(s || '').toLowerCase();
            if (low.includes('cdc')) return 'background:rgba(14,165,233,0.16); color:#38bdf8; border:1px solid rgba(56,189,248,0.35);';
            if (low.includes('seedlog')) return 'background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.35);';
            if (low.includes('công thức') || low.includes('lũy kế')) return 'background:rgba(139,92,246,0.16); color:#c4b5fd; border:1px solid rgba(139,92,246,0.35);';
            if (low.includes('chờ') || low.includes('chưa') || low.includes('mở rộng')) return 'background:rgba(244,63,94,0.14); color:#fda4af; border:1px solid rgba(244,63,94,0.3);';
            return 'background:rgba(30,41,59,0.95); color:#cbd5e1; border:1px solid rgba(255,255,255,0.12);';
        };

        const showMeta = flowColsVis.meta;
        const showUnit = flowColsVis.unit;
        const showSrc = flowColsVis.src;
        const showLogic = flowColsVis.logic;
        const allVisible = showMeta && showUnit && showSrc && showLogic;

        const colBtn = (key, label, active) => `
            <button onclick="toggleFmcgFlowCol('${key}')" title="${active ? 'Bấm để ẨN cột này' : 'Bấm để HIỆN cột này'}"
                style="background:${active ? 'rgba(16,185,129,0.16)' : '#1e293b'}; color:${active ? '#34d399' : '#64748b'}; border:1px solid ${active ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.1)'}; border-radius:6px; padding:0.24rem 0.55rem; font-size:0.72rem; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:0.28rem;">
                <i class="fa-solid ${active ? 'fa-eye' : 'fa-eye-slash'}" style="font-size:0.68rem;"></i> ${label}
            </button>`;

        const hideX = (key, title) => `<span onclick="event.stopPropagation(); toggleFmcgFlowCol('${key}')" title="Ẩn cột ${title}" style="margin-left:5px; cursor:pointer; color:#64748b; font-weight:800; padding:0 3px; border-radius:3px; background:rgba(255,255,255,0.06);">×</span>`;

        const totalColSpan = 3 + (showMeta ? 3 : 0) + (showUnit ? 1 : 0) + (showSrc ? 1 : 0) + (showLogic ? 1 : 0) + 1 + otherCols.length;

        let html = `
            <div style="padding:0.65rem 0.9rem; background:#0f172a; border-bottom:1px solid rgba(255,255,255,0.08); display:flex; flex-direction:column; gap:0.5rem; position:sticky; left:0; z-index:28;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                    <div style="display:flex; align-items:center; gap:0.32rem; flex-wrap:wrap;">
                        <span style="font-size:0.7rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-right:0.2rem;">Điểm chặn:</span>
                        ${blockPills.map(p => {
            const act = flowBlockFilter === p.id;
            return `<button onclick="setFmcgFlowBlock('${p.id}')" style="background:${act ? '#0284c7' : '#1e293b'}; color:${act ? '#fff' : '#94a3b8'}; border:1px solid ${act ? '#38bdf8' : 'rgba(255,255,255,0.08)'}; border-radius:6px; padding:0.25rem 0.56rem; font-size:0.73rem; font-weight:600; cursor:pointer;">${p.label}</button>`;
        }).join('')}
                    </div>
                    <button onclick="toggleFmcgFlowSummaryOnly()" style="background:${flowSummaryOnly ? 'rgba(245,158,11,0.2)' : '#1e293b'}; color:${flowSummaryOnly ? '#fbbf24' : '#cbd5e1'}; border:1px solid ${flowSummaryOnly ? '#f59e0b' : 'rgba(255,255,255,0.12)'}; border-radius:6px; padding:0.26rem 0.65rem; font-size:0.73rem; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:0.3rem;">
                        <i class="fa-solid ${flowSummaryOnly ? 'fa-calendar-days' : 'fa-compress'}"></i>
                        ${flowSummaryOnly ? 'Đang gọn: Σ T11 & Σ Tuần' : 'Thu gọn: Chỉ xem Σ T11 & Σ Tuần'}
                    </button>
                </div>

                <div style="display:flex; align-items:center; gap:0.38rem; flex-wrap:wrap; padding-top:0.42rem; border-top:1px dashed rgba(255,255,255,0.08);">
                    <span style="font-size:0.7rem; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-right:0.15rem;"><i class="fa-solid fa-sliders" style="margin-right:3px; color:#38bdf8;"></i>Ẩn / Hiện Cột:</span>
                    ${colBtn('meta', 'A–C: Miền/Kho/Nhóm', showMeta)}
                    ${colBtn('unit', 'F: Đơn vị', showUnit)}
                    ${colBtn('src', 'G: Nguồn', showSrc)}
                    ${colBtn('logic', 'H: Cách tính & Logic', showLogic)}
                    <span style="color:#334155; margin:0 2px;">|</span>
                    <button onclick="toggleFmcgFlowCol('compact')" style="background:rgba(56,189,248,0.14); color:#38bdf8; border:1px solid rgba(56,189,248,0.35); border-radius:6px; padding:0.24rem 0.58rem; font-size:0.72rem; font-weight:700; cursor:pointer;">
                        <i class="fa-solid fa-bolt"></i> Gọn Xem Số Liệu
                    </button>
                    <button onclick="toggleFmcgFlowCol('all_on')" style="background:${allVisible ? 'rgba(139,92,246,0.22)' : '#1e293b'}; color:${allVisible ? '#c4b5fd' : '#94a3b8'}; border:1px solid ${allVisible ? 'rgba(139,92,246,0.45)' : 'rgba(255,255,255,0.12)'}; border-radius:6px; padding:0.24rem 0.58rem; font-size:0.72rem; font-weight:700; cursor:pointer;">
                        <i class="fa-solid fa-table-columns"></i> Hiện Đủ A–H
                    </button>
                </div>
            </div>

            <table style="width:max-content; min-width:100%; border-collapse:collapse; font-size:0.76rem; text-align:right;">
                <thead>
                    <tr style="background:#0f172a; position:sticky; top:0; z-index:22; border-bottom:2px solid rgba(56,189,248,0.3);">
                        <th style="background:#0f172a; width:34px; min-width:34px; text-align:center; padding:0.55rem 0.25rem; color:#64748b; font-weight:800; border-right:1px solid rgba(255,255,255,0.06);">STT</th>
                        ${showMeta ? `
                            <th style="background:#0f172a; min-width:68px; text-align:left; padding:0.55rem 0.4rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">MIỀN (A)${hideX('meta', 'Miền/Kho/Nhóm')}</th>
                            <th style="background:#0f172a; min-width:50px; text-align:left; padding:0.55rem 0.4rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">KHO (B)</th>
                            <th style="background:#0f172a; min-width:74px; text-align:left; padding:0.55rem 0.4rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">NHÓM (C)</th>
                        ` : ''}
                        <th style="background:#0f172a; width:42px; min-width:42px; text-align:center; padding:0.55rem 0.28rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">ĐC</th>
                        <th style="position:sticky; left:0; z-index:26; background:#0b1325; min-width:195px; max-width:230px; text-align:left; padding:0.55rem 0.6rem; color:#38bdf8; font-weight:800; border-right:2px solid rgba(56,189,248,0.32); box-shadow:2px 0 6px rgba(0,0,0,0.45); white-space:nowrap;">TIÊU CHÍ (E · MAP BẢNG 1)</th>
                        ${showUnit ? `
                            <th style="background:#0f172a; min-width:96px; text-align:center; padding:0.55rem 0.35rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.08); white-space:nowrap;">ĐƠN VỊ (F)${hideX('unit', 'Đơn vị')}</th>
                        ` : ''}
                        ${showSrc ? `
                            <th style="background:#0f172a; min-width:112px; text-align:left; padding:0.55rem 0.42rem; color:#94a3b8; font-weight:800; border-right:1px solid rgba(255,255,255,0.08); white-space:nowrap;">NGUỒN (G)${hideX('src', 'Nguồn')}</th>
                        ` : ''}
                        ${showLogic ? `
                            <th style="background:#0f172a; min-width:190px; max-width:240px; text-align:left; padding:0.55rem 0.45rem; color:#94a3b8; font-weight:800; border-right:2px solid rgba(56,189,248,0.22); white-space:nowrap;">CÁCH TÍNH &amp; LOGIC (H)${hideX('logic', 'Cách tính')}</th>
                        ` : ''}
                        <th style="background:#172554; min-width:114px; text-align:right; padding:0.55rem 0.5rem; color:#fbbf24; font-weight:800; border-right:2px solid rgba(251,191,36,0.35);">
                            <div style="font-size:0.78rem;">${monthCol.label}</div>
                            <div style="font-size:0.63rem; color:#93c5fd; font-weight:500;">${monthCol.sub}</div>
                        </th>
        `;

        otherCols.forEach(c => {
            const isWk = c.type === 'week';
            html += `
                <th style="min-width:${isWk ? '106px' : '90px'}; padding:0.52rem 0.42rem; text-align:right; color:${isWk ? '#38bdf8' : '#e2e8f0'}; font-weight:${isWk ? '800' : '600'}; background:${isWk ? '#0c2444' : '#0f172a'}; border-right:${isWk ? '2px solid rgba(56,189,248,0.3)' : '1px solid rgba(255,255,255,0.05)'};">
                    <div style="font-size:0.76rem; font-family:'JetBrains Mono', monospace;">${c.label}</div>
                    <div style="font-size:0.62rem; color:${isWk ? '#7dd3fc' : '#64748b'}; font-weight:500;">${c.sub}</div>
                </th>
            `;
        });
        html += `</tr></thead><tbody>`;

        let totalRowsShown = 0;
        ft.blocks.forEach(blk => {
            if (flowBlockFilter !== 'all' && blk.id !== flowBlockFilter) return;

            html += `
                <tr style="background:linear-gradient(90deg, ${blk.accent}24, rgba(15,23,42,0.95)); border-top:1px solid rgba(255,255,255,0.12); border-bottom:1px solid rgba(255,255,255,0.08);">
                    <td colspan="${totalColSpan}" style="padding:0.48rem 0.75rem; text-align:left; font-weight:800; color:${blk.accent}; font-size:0.78rem; letter-spacing:0.3px;">
                        <span style="position:sticky; left:12px; display:inline-block;">
                            <i class="${blk.icon}" style="margin-right:0.4rem;"></i> ${blk.title}
                            <span style="font-size:0.7rem; color:#94a3b8; font-weight:600; margin-left:6px;">(${blk.rows.length} chỉ số)</span>
                        </span>
                    </td>
                </tr>
            `;

            blk.rows.forEach((r, idx) => {
                totalRowsShown++;
                const isEven = idx % 2 === 0;
                const rowBg = r.is_empty_template ? '#0d1117' : (isEven ? '#161b22' : '#11161d');
                const dvColor = r.don_vi.includes('%') ? '#c084fc' : (r.don_vi.includes('VND') ? '#fbbf24' : (r.don_vi.includes('SKU') ? '#f472b6' : (r.don_vi.includes('ST') ? '#38bdf8' : '#34d399')));
                const t1Badge = r.t1_idx ? `<span style="display:inline-block; margin-left:4px; padding:0 5px; border-radius:8px; background:rgba(56,189,248,0.14); color:#38bdf8; border:1px solid rgba(56,189,248,0.35); font-size:0.65rem; font-weight:700; font-family:'JetBrains Mono', monospace;" title="Khớp Chỉ số #${r.t1_idx} ở Bảng 1 (53 Chỉ Số)">#${r.t1_idx}</span>` : '';

                html += `
                    <tr style="background:${rowBg}; border-bottom:1px solid rgba(255,255,255,0.04); opacity:${r.is_empty_template ? '0.72' : '1'};">
                        <td style="text-align:center; padding:0.42rem 0.25rem; font-weight:700; color:#64748b; font-size:0.71rem; font-family:'JetBrains Mono', monospace; border-right:1px solid rgba(255,255,255,0.05);">${totalRowsShown}</td>
                        ${showMeta ? `
                            <td style="text-align:left; padding:0.42rem 0.4rem; color:#94a3b8; font-size:0.72rem; white-space:nowrap; border-right:1px solid rgba(255,255,255,0.05);">${escapeHtml(r.mien || 'Miền Nam')}</td>
                            <td style="text-align:left; padding:0.42rem 0.4rem; color:#38bdf8; font-weight:700; font-size:0.72rem; white-space:nowrap; border-right:1px solid rgba(255,255,255,0.05);">${escapeHtml(r.kho || 'FMCG')}</td>
                            <td style="text-align:left; padding:0.42rem 0.4rem; color:#cbd5e1; font-size:0.72rem; white-space:nowrap; border-right:1px solid rgba(255,255,255,0.05);">${escapeHtml(r.nhom || (blk.id === 'B1' ? 'B. Tồn âm' : 'A. Đối soát'))}</td>
                        ` : ''}
                        <td style="text-align:center; padding:0.42rem 0.28rem; font-weight:800; color:${blk.accent}; font-size:0.72rem; border-right:1px solid rgba(255,255,255,0.06);">${r.diem_chan}</td>
                        <td style="position:sticky; left:0; z-index:13; background:${rowBg}; text-align:left; padding:0.42rem 0.55rem; font-weight:700; color:${r.is_empty_template ? '#94a3b8' : '#f1f5f9'}; border-right:2px solid rgba(56,189,248,0.28); box-shadow:2px 0 5px rgba(0,0,0,0.32); min-width:195px; max-width:230px; white-space:normal; line-height:1.28;" title="${escapeHtml((r.nguon || '') + ' — ' + (r.cach_tinh || ''))}">${escapeHtml(r.tieu_chi)}${t1Badge}</td>
                        ${showUnit ? `
                            <td style="text-align:center; padding:0.42rem 0.35rem; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">
                                <span style="font-size:0.67rem; font-weight:700; color:${dvColor}; background:${dvColor}1a; padding:2px 5px; border-radius:4px;">${escapeHtml(r.don_vi)}</span>
                            </td>
                        ` : ''}
                        ${showSrc ? `
                            <td style="text-align:left; padding:0.42rem 0.4rem; border-right:1px solid rgba(255,255,255,0.06); white-space:nowrap;">
                                <span style="display:inline-block; padding:2px 6px; border-radius:4px; font-size:0.67rem; font-weight:700; ${srcBadgeStyle(r.nguon)}">${escapeHtml(r.nguon || '')}</span>
                            </td>
                        ` : ''}
                        ${showLogic ? `
                            <td style="text-align:left; padding:0.42rem 0.45rem; color:#94a3b8; font-size:0.7rem; line-height:1.32; min-width:190px; max-width:240px; white-space:normal; border-right:2px solid rgba(56,189,248,0.18);">${escapeHtml(r.cach_tinh || '')}</td>
                        ` : ''}
                        <td style="background:${isEven ? '#172033' : '#131b2b'}; padding:0.42rem 0.5rem; border-right:2px solid rgba(251,191,36,0.25); font-family:'JetBrains Mono', monospace; font-size:0.75rem; font-weight:800; color:#fde68a; white-space:nowrap;">
                            ${r.values[monthCol.key] || '-'}
                        </td>
                `;

                otherCols.forEach(c => {
                    const val = r.values[c.key] || '-';
                    const isWk = c.type === 'week';
                    const wkBg = isWk ? (isEven ? '#0e223d' : '#0a1b33') : '';
                    html += `
                        <td style="padding:0.42rem 0.42rem; ${wkBg ? 'background:' + wkBg + ';' : ''} border-right:${isWk ? '2px solid rgba(56,189,248,0.22)' : '1px solid rgba(255,255,255,0.04)'}; font-family:'JetBrains Mono', monospace; font-size:0.74rem; white-space:nowrap; font-weight:${isWk ? '700' : '400'};">
                            ${formatCellValue(val, r.tieu_chi)}
                        </td>
                    `;
                });

                html += `</tr>`;
            });
        });

        html += `</tbody></table>`;
        container.innerHTML = html;
        updateStatusText(`<strong>Đối Soát FMCG (${totalAll} Chỉ Số • Đ0–Đ4 + B. Tồn âm)</strong> • Đang hiện <strong>${totalRowsShown}</strong> dòng • Tự động gộp <strong>Σ T11 &amp; Σ Tuần</strong> từ CDC StarRocks + Seedlog • Cập nhật: <strong>${currentData.updated_at || ''}</strong>`);
    }

    function fmtVndClean(strVal) {
        if (!strVal) return '0';
        const num = parseFloat(String(strVal).replace(/,/g, ''));
        if (isNaN(num)) return strVal;
        return Math.round(num).toLocaleString('en-US');
    }

    function fmtVndShort(strVal) {
        if (!strVal) return '';
        const num = parseFloat(String(strVal).replace(/,/g, ''));
        if (isNaN(num)) return '';
        const abs = Math.abs(num);
        const sign = num < 0 ? '-' : '';
        if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)} tỷ`;
        if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)} tr`;
        return `${sign}${Math.round(abs).toLocaleString('en-US')} đ`;
    }

    function renderKPICards() {
        const s = currentData.summary || {};
        const kpiContainer = document.getElementById('fmcg-kpi-cards');
        if (!kpiContainer) return;

        const cards = [
            {
                icon: 'fa-solid fa-chart-line', color: '#38bdf8', valColor: '#7dd3fc',
                label: 'Tổng Chuyển Lũy Kế',
                value: fmtVndClean(s.tong_luy_ke), unit: 'VNĐ',
                sub: `≈ ${fmtVndShort(s.tong_luy_ke)} • Lũy kế 01/11 → ${s.latest_cdc_date || s.latest_date || ''}`
            },
            {
                icon: 'fa-solid fa-scale-unbalanced', color: '#f59e0b', valColor: '#fcd34d',
                label: 'Tồn Kho Chênh Lệch',
                value: fmtVndClean(s.ton_kho_chenh_lech), unit: 'VNĐ',
                sub: `≈ ${fmtVndShort(s.ton_kho_chenh_lech)} • Lũy kế theo gia_cost CDC`
            },
            {
                icon: 'fa-solid fa-percent', color: '#f43f5e', valColor: '#fda4af',
                label: 'Tỷ Lệ Lệch Chuyển Hàng',
                value: s.ty_le_chenh_lech || '0.00%', unit: '',
                sub: 'Tồn kho chênh lệch / Tổng GT lũy kế'
            }
        ];

        kpiContainer.innerHTML = cards.map(c => `
            <div class="kpi-fmcg-card" style="background:#202b3d; border:1px solid rgba(255,255,255,0.09); border-left:3px solid ${c.color}; border-radius:10px; padding:0.9rem 1.1rem; display:flex; align-items:center; gap:0.9rem; min-width:0; overflow:hidden;">
                <div style="width:44px; height:44px; border-radius:10px; background:${c.color}1a; color:${c.color}; border:1px solid ${c.color}33; display:flex; align-items:center; justify-content:center; font-size:1.25rem; flex-shrink:0;">
                    <i class="${c.icon}"></i>
                </div>
                <div style="min-width:0; flex:1;">
                    <div style="font-size:0.72rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.label}</div>
                    <div style="font-size:1.22rem; font-weight:800; color:${c.valColor}; font-family:'JetBrains Mono', monospace; margin:0.18rem 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${c.value} ${c.unit}">
                        ${c.value}${c.unit ? ` <span style="font-size:0.72rem; font-weight:600; color:#cbd5e1;">${c.unit}</span>` : ''}
                    </div>
                    <div style="font-size:0.72rem; color:#94a3b8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${c.sub}">${c.sub}</div>
                </div>
            </div>
        `).join('');
    }

    // ==================== VIEW 1: BẢNG MA TRẬN 53 CHỈ SỐ ====================
    function renderMatrixTable() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;

        let dates = [...currentData.dates];
        if (sortDescending) dates.reverse();

        const sections = currentData.sections || [];
        const q = searchQuery.trim().toLowerCase();

        let tableHtml = `
            <table class="fmcg-matrix-table" style="width:100%; border-collapse:collapse; font-size:0.83rem; text-align:right;">
                <thead>
                    <tr style="background:#0f172a; position:sticky; top:0; z-index:20; border-bottom:1px solid rgba(255,255,255,0.12);">
                        <th style="position:sticky; left:0; z-index:26; background:#0f172a; min-width:44px; max-width:44px; text-align:center; padding:0.8rem 0.3rem; color:#64748b; font-weight:800; border-right:1px solid rgba(255,255,255,0.08);">STT</th>
                        <th style="position:sticky; left:44px; z-index:26; background:#0f172a; min-width:260px; max-width:300px; text-align:left; padding:0.8rem 0.85rem; color:#38bdf8; font-weight:800; border-right:1px solid rgba(255,255,255,0.12);">
                            <div style="display:flex; align-items:center; justify-content:space-between;">
                                <span>CHỈ SỐ LOGISTICS FMCG</span>
                                <span style="font-size:0.68rem; font-weight:600; color:#94a3b8; background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px;">Bấm ⓘ xem logic</span>
                            </div>
                        </th>
                        <th style="position:sticky; left:304px; z-index:25; background:#172554; min-width:130px; text-align:right; padding:0.8rem 0.7rem; color:#fbbf24; font-weight:800; border-right:2px solid rgba(251,191,36,0.35); box-shadow: 2px 0 6px rgba(0,0,0,0.45);">
                            <div style="font-size:0.8rem;">TỔNG / LŨY KẾ</div>
                            <div style="font-size:0.68rem; color:#93c5fd; font-weight:500;">${dates.length} ngày T11</div>
                        </th>
        `;

        dates.forEach(d => {
            const isToday = isDateCurrent(d.iso);
            tableHtml += `
                <th style="min-width:112px; padding:0.72rem 0.6rem; text-align:right; color:${isToday ? '#38bdf8' : '#e2e8f0'}; font-weight:700; border-right:1px solid rgba(255,255,255,0.06); background:${isToday ? 'rgba(56,189,248,0.12)' : '#0f172a'};">
                    <div style="font-size:0.82rem; font-family:'JetBrains Mono', monospace;">${d.display}</div>
                    <div style="font-size:0.68rem; color:#64748b; font-weight:500;">${getDayOfWeek(d.iso)}</div>
                </th>
            `;
        });

        tableHtml += `</tr></thead><tbody>`;
        let visibleRowsCount = 0;

        sections.forEach(sec => {
            if (filterSection !== 'all' && sec.id !== filterSection) return;
            const filteredRows = sec.rows.filter(r => !q || r.name.toLowerCase().includes(q));
            if (filteredRows.length === 0) return;

            visibleRowsCount += filteredRows.length;

            tableHtml += `
                <tr style="background:#182130; border-top:1px solid rgba(255,255,255,0.12); border-bottom:1px solid rgba(255,255,255,0.08);">
                    <td colspan="${dates.length + 3}" style="position:sticky; left:0; z-index:15; padding:0.6rem 0.9rem; text-align:left; font-weight:800; color:${sec.accent}; font-size:0.83rem; letter-spacing:0.4px;">
                        <i class="${sec.icon}" style="margin-right:0.55rem;"></i> ${sec.title}
                    </td>
                </tr>
            `;

            filteredRows.forEach((rowItem, rIdx) => {
                const isEven = rIdx % 2 === 0;
                const rowBg = isEven ? '#1d283a' : '#182232';
                const hasLogic = !!rowItem.logic;
                tableHtml += `
                    <tr class="fmcg-data-row" style="background:${rowBg}; border-bottom:1px solid rgba(255,255,255,0.04);">
                        <td style="position:sticky; left:0; z-index:13; background:${rowBg}; text-align:center; padding:0.58rem 0.3rem; font-weight:700; color:#64748b; font-size:0.75rem; font-family:'JetBrains Mono', monospace; border-right:1px solid rgba(255,255,255,0.06);">${rowItem.row_idx}</td>
                        <td style="position:sticky; left:44px; z-index:13; background:${rowBg}; text-align:left; padding:0.58rem 0.85rem; font-weight:600; color:#cbd5e1; border-right:1px solid rgba(255,255,255,0.08); white-space:nowrap;">
                            <div style="display:flex; align-items:center; justify-content:space-between; gap:0.5rem;">
                                <span>${formatMetricTitle(rowItem.name)}</span>
                                ${hasLogic ? `<button onclick="showFmcgRowLogic(${rowItem.row_idx})" title="Xem logic & công thức lấy dữ liệu dòng này" style="background:rgba(148,163,184,0.08); color:#cbd5e1; border:1px solid rgba(56,189,248,0.28); border-radius:50%; width:20px; height:20px; font-size:0.68rem; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;">i</button>` : ''}
                            </div>
                        </td>
                        <td style="position:sticky; left:304px; z-index:12; background:${isEven ? '#172033' : '#131b2b'}; padding:0.58rem 0.7rem; border-right:2px solid rgba(251,191,36,0.25); font-family:'JetBrains Mono', monospace; font-size:0.81rem; font-weight:700; color:#fde68a; white-space:nowrap; box-shadow: 2px 0 5px rgba(0,0,0,0.35);">
                            ${rowItem.total || '-'}
                        </td>
                `;

                dates.forEach(d => {
                    const val = rowItem.values[d.iso] || '';
                    tableHtml += `
                        <td style="padding:0.58rem 0.6rem; border-right:1px solid rgba(255,255,255,0.04); font-family:'JetBrains Mono', monospace; font-size:0.8rem; white-space:nowrap;">
                            ${formatCellValue(val, rowItem.name)}
                        </td>
                    `;
                });

                tableHtml += `</tr>`;
            });
        });

        if (visibleRowsCount === 0) {
            tableHtml += `
                <tr>
                    <td colspan="${dates.length + 2}" style="padding:2.5rem; text-align:center; color:#64748b;">
                        Không tìm thấy chỉ số nào khớp với từ khóa "<strong>${escapeHtml(searchQuery)}</strong>"
                    </td>
                </tr>`;
        }

        tableHtml += `</tbody></table>`;
        container.innerHTML = tableHtml;
        updateStatusText(`Đang hiển thị <strong>${visibleRowsCount}</strong> chỉ số • <strong>${dates.length}</strong> ngày (01/11 → ${currentData.dates[currentData.dates.length - 1].display}) • Cập nhật: <strong>${currentData.updated_at || ''}</strong>`);
    }

    // ==================== VIEW 2: ĐẶC TẢ LOGIC CHI TIẾT (HÀNG & CỘT) ====================
    function renderLogicView() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;

        const colLogic = currentData.col_logic || [];
        const sections = currentData.sections || [];
        const q = searchQuery.trim().toLowerCase();

        let html = `
            <div style="padding:1.25rem; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; padding-bottom:0.85rem; border-bottom:1px solid rgba(255,255,255,0.1);">
                    <div>
                        <h3 style="margin:0 0 0.25rem 0; color:#e2e8f0; font-size:0.98rem; font-weight:600;">
                            <i class="fa-solid fa-book-open" style="margin-right:0.45rem;"></i> ĐẶC TẢ LOGIC CHI TIẾT CỦA CẢ 2 BẢNG (ĐỐI SOÁT FMCG 53 CHỈ SỐ &amp; 113 CHỈ SỐ)
                        </h3>
                        <p style="margin:0; font-size:0.78rem; color:#94a3b8;">
                            Tài liệu kỹ thuật trực tiếp gắn liền với bộ máy tính toán CDC StarRocks (lọc chặt user hệ thống <code>TKE_WMS</code>) + Google Sheet Seedlog — đầy đủ cho cả 2 bảng.
                        </p>
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                        <button onclick="copyFmcgLogicMarkdown()" style="background:#1c2433; color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.45rem 0.85rem; font-size:0.78rem; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:0.4rem;">
                            <i class="fa-solid fa-copy"></i> Copy Toàn Bộ Logic (Markdown)
                        </button>
                        <button onclick="exportFmcgExcel()" style="background:#1c2433; color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.45rem 0.85rem; font-size:0.78rem; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:0.4rem;">
                            <i class="fa-solid fa-file-excel"></i> Tải Excel (Kèm Sheet Logic)
                        </button>
                        <button onclick="exportFmcgPdf('logic')" style="background:#1c2433; color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.45rem 0.85rem; font-size:0.78rem; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:0.4rem;">
                            <i class="fa-solid fa-file-pdf"></i> Tải PDF (Logic 2 Bảng)
                        </button>
                    </div>
                </div>

                <!-- PHẦN A: LOGIC CỘT & NGUYÊN TẮC HỆ THỐNG -->
                <div style="margin-bottom:1.5rem;">
                    <div style="font-size:0.84rem; font-weight:800; color:#cbd5e1; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.75rem;">
                        <i class="fa-solid fa-layer-group" style="margin-right:0.4rem;"></i> PHẦN A: LOGIC CẤU TRÚC CỘT &amp; QUY TẮC TRUY VẤN HỆ THỐNG
                    </div>
                    <div style="display:flex; flex-direction:column; gap:0.65rem;">
        `;

        colLogic.forEach((item, idx) => {
            html += `
                <div style="background:#0f172a; border:1px solid rgba(255,255,255,0.08); border-left:2px solid #64748b; border-radius:10px; padding:0.9rem 1.15rem; width:100%; box-sizing:border-box;">
                    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.4rem;">
                        <div style="color:#f8fafc; font-size:0.88rem; font-weight:800; line-height:1.35;">${idx + 1}. ${escapeHtml(item.title)}</div>
                        <span style="display:inline-block; font-size:0.7rem; font-weight:700; color:#38bdf8; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.25); padding:2px 8px; border-radius:6px;">${escapeHtml(item.source)}</span>
                    </div>
                    <div style="font-size:0.82rem; color:#cbd5e1; line-height:1.55; overflow-wrap:anywhere;">${formatInlineCode(item.detail)}</div>
                </div>
            `;
        });

        html += `
                    </div>
                </div>

                <!-- PHẦN B: LOGIC CHI TIẾT BẢNG 1 (MA TRẬN 53 CHỈ SỐ) -->
                <div style="font-size:0.82rem; font-weight:800; color:#cbd5e1; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.65rem;">
                    <i class="fa-solid fa-table-list" style="margin-right:0.4rem;"></i> PHẦN B: LOGIC CHI TIẾT BẢNG 1 — ĐỐI SOÁT FMCG (53 CHỈ SỐ)
                </div>
                <div style="overflow-x:auto; border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.78rem; text-align:left;">
                        <thead>
                            <tr style="background:#111827; color:#cbd5e1; border-bottom:1px solid rgba(255,255,255,0.12);">
                                <th style="padding:0.65rem 0.6rem; width:42px; text-align:center;">STT</th>
                                <th style="padding:0.65rem 0.7rem; min-width:190px;">Tên Chỉ Số</th>
                                <th style="padding:0.65rem 0.7rem; min-width:130px;">Nguồn Chính</th>
                                <th style="padding:0.65rem 0.7rem; min-width:220px;">Bảng DB / Sheet & Cột Đọc</th>
                                <th style="padding:0.65rem 0.7rem; min-width:280px;">Điều Kiện Lọc & Quy Tắc Xử Lý</th>
                                <th style="padding:0.65rem 0.7rem; min-width:210px;">Công Thức Tính</th>
                                <th style="padding:0.65rem 0.7rem; min-width:140px;">Cột TỔNG</th>
                                <th style="padding:0.65rem 0.7rem; min-width:190px;">Ghi Chú Nghiệp Vụ</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        let countRows = 0;
        sections.forEach(sec => {
            if (filterSection !== 'all' && sec.id !== filterSection) return;
            const rows = sec.rows.filter(r => {
                if (!q) return true;
                const lg = r.logic || {};
                const blob = `${r.name} ${lg.source || ''} ${lg.table_col || ''} ${lg.filter_rule || ''} ${lg.formula || ''} ${lg.note || ''}`.toLowerCase();
                return blob.includes(q);
            });
            if (rows.length === 0) return;

            html += `
                <tr style="background:#182130; border-top:1px solid rgba(255,255,255,0.1);">
                    <td colspan="8" style="padding:0.5rem 0.75rem; font-weight:600; color:#cbd5e1; font-size:0.77rem;">
                        <i class="${sec.icon}" style="margin-right:0.45rem;"></i> ${sec.title}
                    </td>
                </tr>
            `;

            rows.forEach((r, idx) => {
                countRows++;
                const lg = r.logic || {};
                const bg = idx % 2 === 0 ? '#1d283a' : '#182232';
                const srcBadgeColor = (lg.source || '').includes('CDC') ? '#38bdf8' : ((lg.source || '').includes('Seedlog') ? '#34d399' : '#f59e0b');
                html += `
                    <tr style="background:${bg}; border-bottom:1px solid rgba(255,255,255,0.05); vertical-align:top; font-size:0.74rem; font-weight:300;">
                        <td style="padding:0.52rem 0.5rem; text-align:center; color:#64748b; font-weight:400;">${r.row_idx}</td>
                        <td style="padding:0.52rem 0.7rem; font-weight:400; color:#f1f5f9;">${escapeHtml(r.name)}</td>
                        <td style="padding:0.52rem 0.7rem;">
                            <span style="display:inline-block; font-size:0.68rem; font-weight:400; color:#94a3b8; background:rgba(148,163,184,0.1); border:1px solid rgba(148,163,184,0.2); padding:2px 7px; border-radius:6px;">${escapeHtml(lg.source || '')}</span>
                        </td>
                        <td style="padding:0.52rem 0.7rem; color:#cbd5e1; line-height:1.45;">${formatInlineCode(lg.table_col || '')}</td>
                        <td style="padding:0.52rem 0.7rem; color:#cbd5e1; line-height:1.45;">${formatInlineCode(lg.filter_rule || '')}</td>
                        <td style="padding:0.52rem 0.7rem; color:#cbd5e1; font-family:'JetBrains Mono', monospace; font-size:0.72rem; line-height:1.45;">${escapeHtml(lg.formula || '')}</td>
                        <td style="padding:0.52rem 0.7rem; color:#93c5fd;">${escapeHtml(lg.total_rule || '')}</td>
                        <td style="padding:0.52rem 0.7rem; color:#94a3b8; line-height:1.4;">${escapeHtml(lg.note || '')}</td>
                    </tr>
                `;
            });
        });

        html += `</tbody></table></div>`;

        // PHẦN C: LOGIC CHI TIẾT BẢNG 2 (FLOW ĐIỂM CHẶN Đ0–Đ4 + B. TỒN ÂM)
        const ft = currentData.flow_template;
        let flowLogicCount = 0;
        if (ft && ft.blocks && ft.blocks.length > 0) {
            html += `
                <div style="margin-top:1.75rem;">
                    <div style="font-size:0.82rem; font-weight:800; color:#cbd5e1; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.65rem;">
                        <i class="fa-solid fa-diagram-project" style="margin-right:0.4rem;"></i> PHẦN C: LOGIC CHI TIẾT BẢNG 2 — ĐỐI SOÁT FMCG (113 CHỈ SỐ • Đ0–Đ4 + B. TỒN ÂM)
                    </div>
                    <div style="overflow-x:auto; border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
                        <table style="width:100%; border-collapse:collapse; font-size:0.78rem; text-align:left;">
                            <thead>
                                <tr style="background:#111827; color:#cbd5e1; border-bottom:1px solid rgba(255,255,255,0.12);">
                                    <th style="padding:0.65rem 0.5rem; width:44px; text-align:center;">STT</th>
                                    <th style="padding:0.65rem 0.6rem; width:56px; text-align:center;">ĐC</th>
                                    <th style="padding:0.65rem 0.7rem; min-width:210px;">Tiêu Chí (Flow FMCG)</th>
                                    <th style="padding:0.65rem 0.6rem; min-width:110px; text-align:center;">Đơn Vị</th>
                                    <th style="padding:0.65rem 0.7rem; min-width:130px;">Nguồn Chính</th>
                                    <th style="padding:0.65rem 0.7rem; min-width:380px;">Điều Kiện Lọc &amp; Công Thức Chi Tiết</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            let sttFlow = 0;
            ft.blocks.forEach(blk => {
                const matchedRows = blk.rows.map((r, i) => ({ r, stt: sttFlow + i + 1 })).filter(item => {
                    if (!q) return true;
                    const blob = `${item.r.diem_chan} ${item.r.tieu_chi} ${item.r.don_vi} ${item.r.nguon} ${item.r.cach_tinh}`.toLowerCase();
                    return blob.includes(q);
                });
                sttFlow += blk.rows.length;
                if (matchedRows.length === 0) return;

                html += `
                    <tr style="background:#182130; border-top:1px solid rgba(255,255,255,0.1);">
                        <td colspan="6" style="padding:0.5rem 0.75rem; font-weight:600; color:#cbd5e1; font-size:0.77rem;">
                            <i class="${blk.icon}" style="margin-right:0.45rem;"></i> ${blk.title}
                        </td>
                    </tr>
                `;
                matchedRows.forEach(({ r, stt }, idx) => {
                    flowLogicCount++;
                    const bg = r.is_empty_template ? '#141c2b' : (idx % 2 === 0 ? '#1d283a' : '#182232');
                    const srcColor = (r.nguon || '').includes('CDC') ? '#38bdf8' : ((r.nguon || '').includes('Seedlog') ? '#34d399' : '#f59e0b');
                    html += `
                        <tr style="background:${bg}; border-bottom:1px solid rgba(255,255,255,0.05); vertical-align:top; font-size:0.74rem; font-weight:300; opacity:${r.is_empty_template ? '0.68' : '1'};">
                            <td style="padding:0.5rem 0.5rem; text-align:center; color:#64748b; font-weight:400;">${stt}</td>
                            <td style="padding:0.5rem 0.5rem; text-align:center; color:${blk.accent}; font-weight:500;">${escapeHtml(r.diem_chan)}</td>
                            <td style="padding:0.5rem 0.7rem; font-weight:400; color:#f1f5f9;">${escapeHtml(r.tieu_chi)}</td>
                            <td style="padding:0.5rem 0.6rem; text-align:center; color:#cbd5e1;">${escapeHtml(r.don_vi)}</td>
                            <td style="padding:0.5rem 0.7rem;">
                                <span style="display:inline-block; font-size:0.68rem; font-weight:400; color:#94a3b8; background:rgba(148,163,184,0.1); border:1px solid rgba(148,163,184,0.2); padding:2px 7px; border-radius:6px;">${escapeHtml(r.nguon || '')}</span>
                            </td>
                            <td style="padding:0.5rem 0.7rem; color:#cbd5e1; line-height:1.45;">${formatInlineCode(r.cach_tinh || '')}</td>
                        </tr>
                    `;
                });
            });
            html += `</tbody></table></div></div>`;
        }

        html += `</div>`;
        container.innerHTML = html;
        updateStatusText(`Đang xem <strong>Đặc tả Logic chi tiết cả 2 bảng</strong> (Bảng 1: <strong>${countRows}</strong> chỉ số • Bảng 2: <strong>${flowLogicCount}</strong> dòng Flow Đ0–Đ4) • Bấm "Copy Toàn Bộ Logic" hoặc "Tải Excel".`);
    }

    // ==================== VIEW 3: ĐỐI CHIẾU CDC STARROCKS vs SEEDLOG ====================
    function renderReconcileView() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;

        const recs = [...(currentData.reconciliation || [])];
        if (sortDescending) recs.reverse();

        let html = `
            <div style="padding:1.15rem; text-align:left;">
                <div style="margin-bottom:0.85rem;">
                    <h3 style="margin:0 0 0.25rem 0; color:#e2e8f0; font-size:0.96rem; font-weight:600;">
                        <i class="fa-solid fa-circle-check" style="margin-right:0.45rem;"></i> BẢNG ĐỐI CHIẾU KIỂM CHỨNG: CDC STARROCKS (FGA10101 → CHỈ SIÊU THỊ KFM + BẢNG TO) vs SEEDLOG
                    </h3>
                    <p style="margin:0; font-size:0.78rem; color:#94a3b8;">
                        So sánh trực diện từng ngày giữa Database CDC StarRocks (cả 2 chế độ <code>blank=0</code> và <code>blank=-1</code>) với Google Sheet Seedlog (Cột M &lt; 0).
                    </p>
                </div>
                <div style="overflow-x:auto; border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.8rem; text-align:right;">
                        <thead>
                            <tr style="background:#111827; color:#cbd5e1; border-bottom:1px solid rgba(255,255,255,0.12);">
                                <th style="padding:0.65rem 0.45rem; text-align:center; color:#64748b;">STT</th>
                                <th style="padding:0.65rem; text-align:center;">Ngày</th>
                                <th style="padding:0.65rem;">Phiếu PT</th>
                                <th style="padding:0.65rem;">SL Chuyển (CDC)</th>
                                <th style="padding:0.65rem;">SL Nhận Capped</th>
                                <th style="padding:0.65rem;">Lệch CDC (blank=0)</th>
                                <th style="padding:0.65rem;">Lệch CDC (blank=-1)</th>
                                <th style="padding:0.65rem;">Lệch Seedlog (M&lt;0)</th>
                                <th style="padding:0.65rem;">Độ Lệch (blank=0)</th>
                                <th style="padding:0.65rem;">Độ Lệch (blank=-1)</th>
                                <th style="padding:0.65rem;">SL Dư</th>
                                <th style="padding:0.65rem; text-align:left; min-width:260px;">Đánh Giá / Giải Thích</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        recs.forEach((r, idx) => {
            const bg = idx % 2 === 0 ? '#1d283a' : '#182232';
            const badgeStyle = r.status_code === 'ok'
                ? 'color:#34d399; background:rgba(16,185,129,0.14); border:1px solid rgba(16,185,129,0.35);'
                : (r.status_code === 'pending'
                    ? 'color:#94a3b8; background:rgba(148,163,184,0.12); border:1px solid rgba(148,163,184,0.25);'
                    : 'color:#f87171; background:rgba(248,113,113,0.14); border:1px solid rgba(248,113,113,0.35);');

            html += `
                <tr style="background:${bg}; border-bottom:1px solid rgba(255,255,255,0.04); font-family:'JetBrains Mono', monospace; font-size:0.74rem; font-weight:300;">
                    <td style="padding:0.48rem 0.45rem; text-align:center; color:#64748b; font-weight:400;">${idx + 1}</td>
                    <td style="padding:0.48rem 0.65rem; text-align:center; font-weight:500; color:#e2e8f0;">${r.date}</td>
                    <td style="padding:0.48rem 0.65rem; color:#94a3b8;">${fmtNum(r.pt_cnt)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#f1f5f9;">${fmtNum(r.sl_chuyen)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#cbd5e1;">${fmtNum(r.sl_nhan)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#f87171;">${fmtNum(r.cdc_blank0)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#fb7185;">${fmtNum(r.cdc_blank_m1)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#38bdf8; font-weight:500;">${fmtNum(r.seedlog)}</td>
                    <td style="padding:0.48rem 0.65rem; color:${Math.abs(r.diff_0) < 0.1 ? '#34d399' : '#fbbf24'}; font-weight:500;">${fmtNum(r.diff_0)}</td>
                    <td style="padding:0.48rem 0.65rem; color:${Math.abs(r.diff_m1) < 0.1 ? '#34d399' : '#fbbf24'}; font-weight:500;">${fmtNum(r.diff_m1)}</td>
                    <td style="padding:0.48rem 0.65rem; color:#a78bfa;">${fmtNum(r.sl_du)}</td>
                    <td style="padding:0.48rem 0.65rem; text-align:left; font-family:inherit;">
                        <span style="display:inline-block; padding:2px 8px; border-radius:6px; font-size:0.7rem; font-weight:400; ${badgeStyle}">${escapeHtml(r.status_txt)}</span>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table></div></div>`;
        container.innerHTML = html;
        updateStatusText(`Bảng đối chiếu kiểm chứng <strong>${recs.length}</strong> ngày giữa CDC StarRocks và Google Sheet Seedlog.`);
    }

    // ==================== POPUP XEM NHANH LOGIC 1 DÒNG (Bấm nút ⓘ) ====================
    window.showFmcgRowLogic = function (rowIdx) {
        if (!currentData) return;
        let found = null;
        (currentData.sections || []).forEach(sec => {
            sec.rows.forEach(r => { if (r.row_idx === rowIdx) found = r; });
        });
        if (!found || !found.logic) return;
        const lg = found.logic;

        let modal = document.getElementById('fmcg-logic-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'fmcg-logic-modal';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(2,6,23,0.75); z-index:9999; display:flex; align-items:center; justify-content:center; padding:1rem; backdrop-filter:blur(4px);';
            modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div style="background:#0f172a; border:1px solid rgba(56,189,248,0.4); border-radius:14px; max-width:680px; width:100%; padding:1.35rem 1.5rem; box-shadow:0 20px 50px rgba(0,0,0,0.6); color:#e2e8f0; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.1);">
                    <div>
                        <div style="font-size:0.72rem; color:#38bdf8; font-weight:700; text-transform:uppercase;">LOGIC CHỈ SỐ #${lg.stt} • ${escapeHtml(lg.section)}</div>
                        <h3 style="margin:0.2rem 0 0 0; font-size:1.1rem; color:#fff;">${escapeHtml(found.name)}</h3>
                    </div>
                    <button onclick="document.getElementById('fmcg-logic-modal').style.display='none'" style="background:rgba(255,255,255,0.08); color:#cbd5e1; border:none; border-radius:8px; width:30px; height:30px; cursor:pointer; font-size:1rem;">✕</button>
                </div>
                <div style="display:grid; gap:0.7rem; font-size:0.83rem; line-height:1.5;">
                    <div><strong style="color:#94a3b8;">Nguồn dữ liệu chính:</strong> <span style="color:#38bdf8; font-weight:700;">${escapeHtml(lg.source)}</span></div>
                    <div><strong style="color:#94a3b8;">Bảng DB / Sheet & Cột đọc:</strong><div style="background:#1e293b; padding:0.5rem 0.7rem; border-radius:6px; margin-top:0.25rem; color:#e2e8f0;">${formatInlineCode(lg.table_col)}</div></div>
                    <div><strong style="color:#94a3b8;">Điều kiện lọc & Quy tắc xử lý:</strong><div style="background:#1e293b; padding:0.5rem 0.7rem; border-radius:6px; margin-top:0.25rem; color:#e2e8f0;">${formatInlineCode(lg.filter_rule)}</div></div>
                    <div><strong style="color:#94a3b8;">Công thức tính:</strong><div style="background:#172554; padding:0.5rem 0.7rem; border-radius:6px; margin-top:0.25rem; color:#cbd5e1; font-family:'JetBrains Mono', monospace;">${escapeHtml(lg.formula)}</div></div>
                    <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
                        <div><strong style="color:#94a3b8;">Cột TỔNG kỳ:</strong> <span style="color:#93c5fd;">${escapeHtml(lg.total_rule)}</span></div>
                        <div><strong style="color:#94a3b8;">Tổng hiện tại:</strong> <strong style="color:#fbbf24; font-family:'JetBrains Mono', monospace;">${escapeHtml(found.total || '-')}</strong></div>
                    </div>
                    ${lg.note ? `<div><strong style="color:#94a3b8;">Ghi chú nghiệp vụ:</strong> <span style="color:#cbd5e1;">${escapeHtml(lg.note)}</span></div>` : ''}
                </div>
                <div style="margin-top:1.1rem; display:flex; justify-content:flex-end; gap:0.5rem;">
                    <button onclick="document.getElementById('fmcg-logic-modal').style.display='none'; switchFmcgSubView('logic');" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.35); border-radius:8px; padding:0.45rem 0.9rem; font-size:0.78rem; font-weight:700; cursor:pointer;">Xem Toàn Bộ Bảng Logic</button>
                    <button onclick="document.getElementById('fmcg-logic-modal').style.display='none'" style="background:#1e293b; color:#e2e8f0; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:0.45rem 0.9rem; font-size:0.78rem; font-weight:700; cursor:pointer;">Đóng</button>
                </div>
            </div>
        `;
        modal.style.display = 'flex';
    };

    // ==================== COPY TOÀN BỘ LOGIC RA MARKDOWN ====================
    window.copyFmcgLogicMarkdown = function () {
        if (!currentData) return;
        let md = `# ĐẶC TẢ LOGIC BÁO CÁO LOGISTICS KHO KHÔ FMCG (CDC STARROCKS + SEEDLOG)\n`;
        md += `- Cập nhật lúc: ${currentData.updated_at || ''}\n- Phạm vi: ${currentData.filter_scope || ''}\n\n`;
        md += `## PHẦN A: LOGIC CẤU TRÚC CỘT & QUY TẮC HỆ THỐNG\n`;
        (currentData.col_logic || []).forEach((c, i) => {
            md += `${i + 1}. **${c.title}** (${c.source}): ${c.detail}\n`;
        });
        md += `\n## PHẦN B: LOGIC CHI TIẾT 53 HÀNG CHỈ SỐ\n`;
        md += `| STT | Khối | Tên Chỉ Số | Nguồn | Bảng / Cột Đọc | Điều Kiện Lọc | Công Thức | Cột TỔNG | Ghi Chú |\n|---:|---|---|---|---|---|---|---|---|\n`;
        (currentData.sections || []).forEach(sec => {
            sec.rows.forEach(r => {
                const lg = r.logic || {};
                const clean = (s) => String(s || '').replace(/\|/g, '/').replace(/\n/g, ' ');
                md += `| ${r.row_idx} | ${clean(lg.section)} | ${clean(r.name)} | ${clean(lg.source)} | ${clean(lg.table_col)} | ${clean(lg.filter_rule)} | ${clean(lg.formula)} | ${clean(lg.total_rule)} | ${clean(lg.note)} |\n`;
            });
        });

        if (currentData.flow_template && currentData.flow_template.blocks) {
            md += `\n## PHẦN C: LOGIC CHI TIẾT BẢNG 2 — FLOW ĐIỂM CHẶN (Đ0–Đ4 + B. TỒN ÂM)\n`;
            md += `| STT | Điểm Chặn | Tiêu Chí | Đơn Vị | Nguồn | Điều Kiện Lọc & Công Thức |\n|---:|---|---|---|---|---|\n`;
            let sttF = 0;
            currentData.flow_template.blocks.forEach(blk => {
                blk.rows.forEach(r => {
                    sttF++;
                    const clean = (s) => String(s || '').replace(/\|/g, '/').replace(/\n/g, ' ');
                    md += `| ${sttF} | ${clean(r.diem_chan)} | ${clean(r.tieu_chi)} | ${clean(r.don_vi)} | ${clean(r.nguon)} | ${clean(r.cach_tinh)} |\n`;
                });
            });
        }

        navigator.clipboard.writeText(md).then(() => {
            alert('Đã sao chép toàn bộ đặc tả Logic (Phần A + 53 Hàng) dạng Markdown vào Clipboard!');
        }).catch(() => {
            const ta = document.createElement('textarea');
            ta.value = md;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            alert('Đã sao chép toàn bộ đặc tả Logic vào Clipboard!');
        });
    };

    // ==================== XUẤT EXCEL 3 SHEET (MA TRẬN + LOGIC + ĐỐI CHIẾU) ====================
    window.exportFmcgExcel = function () {
        if (!currentData || !currentData.dates || !window.XLSX) {
            alert('Chưa có dữ liệu hoặc thư viện Excel chưa tải xong.');
            return;
        }
        try {
            const wb = XLSX.utils.book_new();
            let dates = [...currentData.dates];
            if (sortDescending) dates.reverse();

            // Sheet 1: Ma Trận
            const ws1Data = [['STT', 'Tên Chỉ Số', 'Nguồn Chính', 'TỔNG / LŨY KẾ', ...dates.map(d => d.display)]];
            currentData.sections.forEach(sec => {
                ws1Data.push(['', `--- ${sec.title} ---`, '', '', ...dates.map(() => '')]);
                sec.rows.forEach(r => {
                    ws1Data.push([r.row_idx, r.name, (r.logic && r.logic.source) || '', r.total || '', ...dates.map(d => r.values[d.iso] || '')]);
                });
            });
            XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws1Data), 'MA_TRAN_FMCG');

            // Sheet 2: Logic Chi Tiết
            const ws2Data = [['PHẦN A: LOGIC CẤU TRÚC CỘT & QUY TẮC HỆ THỐNG'], ['Thành Phần', 'Nguồn', 'Chi Tiết Quy Tắc']];
            (currentData.col_logic || []).forEach(c => ws2Data.push([c.title, c.source, c.detail]));
            ws2Data.push([]);
            ws2Data.push(['PHẦN B: LOGIC CHI TIẾT 53 HÀNG CHỈ SỐ']);
            ws2Data.push(['STT', 'Khối', 'Tên Chỉ Số', 'Nguồn Chính', 'Bảng DB / Sheet & Cột Đọc', 'Điều Kiện Lọc & Quy Tắc', 'Công Thức Tính', 'Cách Tính Cột TỔNG', 'Ghi Chú']);
            currentData.sections.forEach(sec => {
                sec.rows.forEach(r => {
                    const lg = r.logic || {};
                    ws2Data.push([r.row_idx, lg.section || sec.title, r.name, lg.source || '', lg.table_col || '', lg.filter_rule || '', lg.formula || '', lg.total_rule || '', lg.note || '']);
                });
            });
            if (currentData.flow_template && currentData.flow_template.blocks) {
                ws2Data.push([]);
                ws2Data.push(['PHẦN C: LOGIC CHI TIẾT BẢNG 2 — FLOW ĐIỂM CHẶN (Đ0–Đ4 + B. TỒN ÂM)']);
                ws2Data.push(['STT', 'Điểm Chặn', 'Tiêu Chí', 'Đơn Vị', 'Nguồn Chính', 'Điều Kiện Lọc & Công Thức Chi Tiết']);
                let sttF = 0;
                currentData.flow_template.blocks.forEach(blk => {
                    blk.rows.forEach(r => {
                        sttF++;
                        ws2Data.push([sttF, r.diem_chan, r.tieu_chi, r.don_vi, r.nguon, r.cach_tinh]);
                    });
                });
            }
            XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws2Data), 'LOGIC_CHI_TIET');

            // Sheet 3: Đối Chiếu CDC vs Seedlog
            if (currentData.reconciliation && currentData.reconciliation.length > 0) {
                const ws3Data = [['Ngày', 'Số Phiếu PT', 'SL Chuyển (CDC)', 'SL Nhận Capped', 'Lệch CDC (blank=0)', 'Lệch CDC (blank=-1)', 'Lệch Seedlog (M<0)', 'Độ Lệch (blank=0)', 'Độ Lệch (blank=-1)', 'SL Dư', 'Đánh Giá']];
                currentData.reconciliation.forEach(r => {
                    ws3Data.push([r.date, r.pt_cnt, r.sl_chuyen, r.sl_nhan, r.cdc_blank0, r.cdc_blank_m1, r.seedlog, r.diff_0, r.diff_m1, r.sl_du, r.status_txt]);
                });
                XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws3Data), 'DOI_CHIEU_CDC_SEEDLOG');
            }

            // Sheet 4: Flow Điểm Chặn (Đ0-Đ4 + B. Tồn âm)
            if (currentData.flow_template && currentData.flow_template.blocks) {
                const cols = currentData.flow_template.columns;
                const ws4Data = [['Điểm Chặn', 'Tiêu Chí', 'Đơn Vị', 'Nguồn', ...cols.map(c => c.label)]];
                currentData.flow_template.blocks.forEach(blk => {
                    ws4Data.push([blk.id, blk.title, '', '', ...cols.map(() => '')]);
                    blk.rows.forEach(r => {
                        ws4Data.push([r.diem_chan, r.tieu_chi, r.don_vi, r.nguon, ...cols.map(c => r.values[c.key] || '-')]);
                    });
                });
                XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(ws4Data), 'FLOW_DIEM_CHAN_D0_D4');
            }

            const filename = `Bao_Cao_FMCG_Va_Logic_${new Date().toISOString().slice(0, 10)}.xlsx`;
            XLSX.writeFile(wb, filename);
        } catch (err) {
            console.error('Lỗi xuất Excel:', err);
            alert('Lỗi xuất file Excel: ' + err.message);
        }
    };

    // ==================== XUẤT PDF (CHUẨN A4 NGANG, FONT TIẾNG VIỆT VECTOR SẮC NÉT) ====================
    window.exportFmcgPdf = function (overrideView) {
        if (!currentData || !currentData.dates) {
            alert('Chưa có dữ liệu Báo cáo Logistics FMCG để xuất PDF.');
            return;
        }
        const targetView = overrideView || activeSubView || 'matrix';
        const s = currentData.summary || {};
        const viewTitles = {
            matrix: 'BẢNG 1: ĐỐI SOÁT FMCG (53 CHỈ SỐ)',
            flow: 'BẢNG 2: ĐỐI SOÁT FMCG (113 CHỈ SỐ • Đ0–Đ4 + B. TỒN ÂM)',
            logic: 'ĐẶC TẢ LOGIC CHI TIẾT CẢ 2 BẢNG (ĐỐI SOÁT FMCG 53 CHỈ SỐ & 113 CHỈ SỐ)',
            reconcile: 'BẢNG ĐỐI CHIẾU KIỂM CHỨNG: CDC STARROCKS vs SEEDLOG',
            progress: 'BẢNG 5: THEO DÕI TIẾN ĐỘ & XẾP HẠNG SIÊU THỊ FMCG (CHUẨN TAB 2 • KHÔNG NGƯỠNG 100K)'
        };
        const title = viewTitles[targetView] || viewTitles.matrix;
        const dateStr = new Date().toISOString().slice(0, 10);
        const docTitle = `Bao_Cao_FMCG_${targetView.toUpperCase()}_${dateStr}`;

        let bodyHtml = '';

        if (targetView === 'matrix') {
            let dates = [...currentData.dates];
            if (sortDescending) dates.reverse();
            const sections = currentData.sections || [];
            bodyHtml += `<table><thead><tr>
                <th style="width:26px; text-align:center;">STT</th>
                <th style="min-width:140px; text-align:left;">Chỉ Số Logistics FMCG</th>
                <th style="min-width:74px; text-align:right; background:#fef3c7; color:#92400e;">TỔNG / LK</th>
                ${dates.map(d => `<th style="text-align:right;">${escapeHtml(d.short || d.display)}</th>`).join('')}
            </tr></thead><tbody>`;
            sections.forEach(sec => {
                if (filterSection !== 'all' && sec.id !== filterSection) return;
                bodyHtml += `<tr class="sec-row"><td colspan="${dates.length + 3}">${escapeHtml(sec.title)}</td></tr>`;
                sec.rows.forEach(r => {
                    bodyHtml += `<tr>
                        <td style="text-align:center; color:#64748b;">${r.row_idx}</td>
                        <td style="text-align:left; font-weight:600;">${escapeHtml(r.name)}</td>
                        <td style="text-align:right; font-weight:700; background:#fffbeb;">${escapeHtml(r.total || '-')}</td>
                        ${dates.map(d => {
                        const v = r.values[d.iso] || '-';
                        const neg = String(v).startsWith('-');
                        return `<td style="text-align:right;${neg ? ' color:#b91c1c; font-weight:700;' : ''}">${escapeHtml(v)}</td>`;
                    }).join('')}
                    </tr>`;
                });
            });
            bodyHtml += `</tbody></table>`;
        } else if (targetView === 'flow' && currentData.flow_template && currentData.flow_template.blocks) {
            const ft = currentData.flow_template;
            const monthCol = ft.columns.find(c => c.type === 'month') || ft.columns[0];
            let otherCols = ft.columns.filter(c => c.key !== monthCol.key);
            if (flowSummaryOnly) otherCols = otherCols.filter(c => c.type === 'week');
            if (sortDescending) otherCols = [...otherCols].reverse();
            bodyHtml += `<table><thead><tr>
                <th style="width:24px; text-align:center;">STT</th>
                <th style="width:28px; text-align:center;">ĐC</th>
                <th style="min-width:130px; text-align:left;">Tiêu Chí (Flow FMCG)</th>
                <th style="width:58px; text-align:center;">Đơn Vị</th>
                <th style="min-width:70px; text-align:right; background:#fef3c7; color:#92400e;">${escapeHtml(monthCol.label)}</th>
                ${otherCols.map(c => `<th style="text-align:right;${c.type === 'week' ? ' background:#dbeafe; color:#1e3a8a;' : ''}">${escapeHtml(c.label)}</th>`).join('')}
            </tr></thead><tbody>`;
            let stt = 0;
            ft.blocks.forEach(blk => {
                if (flowBlockFilter !== 'all' && blk.id !== flowBlockFilter) return;
                bodyHtml += `<tr class="sec-row"><td colspan="${otherCols.length + 5}">${escapeHtml(blk.title)}</td></tr>`;
                blk.rows.forEach(r => {
                    stt++;
                    bodyHtml += `<tr${r.is_empty_template ? ' style="color:#94a3b8;"' : ''}>
                        <td style="text-align:center; color:#64748b;">${stt}</td>
                        <td style="text-align:center; font-weight:700;">${escapeHtml(r.diem_chan)}</td>
                        <td style="text-align:left; font-weight:600;">${escapeHtml(r.tieu_chi)}</td>
                        <td style="text-align:center;">${escapeHtml(r.don_vi)}</td>
                        <td style="text-align:right; font-weight:700; background:#fffbeb;">${escapeHtml(r.values[monthCol.key] || '-')}</td>
                        ${otherCols.map(c => {
                        const v = r.values[c.key] || '-';
                        const neg = String(v).startsWith('-');
                        return `<td style="text-align:right;${c.type === 'week' ? ' background:#eff6ff; font-weight:700;' : ''}${neg ? ' color:#b91c1c; font-weight:700;' : ''}">${escapeHtml(v)}</td>`;
                    }).join('')}
                    </tr>`;
                });
            });
            bodyHtml += `</tbody></table>`;
        } else if (targetView === 'logic') {
            bodyHtml += `<h3>PHẦN A: LOGIC CẤU TRÚC CỘT &amp; QUY TẮC TRUY VẤN HỆ THỐNG</h3>`;
            bodyHtml += `<table class="logic-tbl"><thead><tr>
                <th style="width:26px; text-align:center;">#</th>
                <th style="width:180px; text-align:left;">Thành Phần</th>
                <th style="width:120px; text-align:left;">Nguồn</th>
                <th style="text-align:left;">Quy Tắc Chi Tiết</th>
            </tr></thead><tbody>`;
            (currentData.col_logic || []).forEach((c, i) => {
                bodyHtml += `<tr>
                    <td style="text-align:center;">${i + 1}</td>
                    <td style="font-weight:700;">${escapeHtml(c.title)}</td>
                    <td>${escapeHtml(c.source)}</td>
                    <td>${escapeHtml(c.detail).replace(/\*\*/g, '')}</td>
                </tr>`;
            });
            bodyHtml += `</tbody></table>`;

            bodyHtml += `<h3>PHẦN B: LOGIC CHI TIẾT BẢNG 1 — MA TRẬN 53 CHỈ SỐ</h3>`;
            bodyHtml += `<table class="logic-tbl"><thead><tr>
                <th style="width:24px; text-align:center;">STT</th>
                <th style="width:120px; text-align:left;">Tên Chỉ Số</th>
                <th style="width:82px; text-align:left;">Nguồn</th>
                <th style="width:150px; text-align:left;">Bảng / Cột Đọc</th>
                <th style="text-align:left;">Điều Kiện Lọc &amp; Quy Tắc Xử Lý</th>
                <th style="width:130px; text-align:left;">Công Thức</th>
                <th style="width:80px; text-align:left;">Cột TỔNG</th>
            </tr></thead><tbody>`;
            (currentData.sections || []).forEach(sec => {
                bodyHtml += `<tr class="sec-row"><td colspan="7">${escapeHtml(sec.title)}</td></tr>`;
                sec.rows.forEach(r => {
                    const lg = r.logic || {};
                    bodyHtml += `<tr>
                        <td style="text-align:center;">${r.row_idx}</td>
                        <td style="font-weight:700;">${escapeHtml(r.name)}</td>
                        <td>${escapeHtml(lg.source || '')}</td>
                        <td>${escapeHtml(lg.table_col || '')}</td>
                        <td>${escapeHtml(lg.filter_rule || '')}</td>
                        <td style="font-family:Consolas, monospace;">${escapeHtml(lg.formula || '')}</td>
                        <td>${escapeHtml(lg.total_rule || '')}</td>
                    </tr>`;
                });
            });
            bodyHtml += `</tbody></table>`;

            if (currentData.flow_template && currentData.flow_template.blocks) {
                bodyHtml += `<h3 style="page-break-before:always;">PHẦN C: LOGIC CHI TIẾT BẢNG 2 — FLOW ĐIỂM CHẶN (Đ0–Đ4 + B. TỒN ÂM)</h3>`;
                bodyHtml += `<table class="logic-tbl"><thead><tr>
                    <th style="width:24px; text-align:center;">STT</th>
                    <th style="width:32px; text-align:center;">ĐC</th>
                    <th style="width:170px; text-align:left;">Tiêu Chí</th>
                    <th style="width:76px; text-align:center;">Đơn Vị</th>
                    <th style="width:92px; text-align:left;">Nguồn</th>
                    <th style="text-align:left;">Điều Kiện Lọc &amp; Công Thức Chi Tiết</th>
                </tr></thead><tbody>`;
                let sttF = 0;
                currentData.flow_template.blocks.forEach(blk => {
                    bodyHtml += `<tr class="sec-row"><td colspan="6">${escapeHtml(blk.title)}</td></tr>`;
                    blk.rows.forEach(r => {
                        sttF++;
                        bodyHtml += `<tr>
                            <td style="text-align:center;">${sttF}</td>
                            <td style="text-align:center; font-weight:700;">${escapeHtml(r.diem_chan)}</td>
                            <td style="font-weight:700;">${escapeHtml(r.tieu_chi)}</td>
                            <td style="text-align:center;">${escapeHtml(r.don_vi)}</td>
                            <td>${escapeHtml(r.nguon)}</td>
                            <td>${escapeHtml(r.cach_tinh)}</td>
                        </tr>`;
                    });
                });
                bodyHtml += `</tbody></table>`;
            }
        } else if (targetView === 'reconcile') {
            let recs = [...(currentData.reconciliation || [])];
            if (sortDescending) recs.reverse();
            bodyHtml += `<table class="logic-tbl"><thead><tr>
                <th style="text-align:center;">STT</th>
                <th style="text-align:center;">Ngày</th>
                <th style="text-align:right;">Phiếu PT</th>
                <th style="text-align:right;">SL Chuyển</th>
                <th style="text-align:right;">SL Nhận Capped</th>
                <th style="text-align:right;">Lệch CDC (0)</th>
                <th style="text-align:right;">Lệch CDC (-1)</th>
                <th style="text-align:right;">Lệch Seedlog</th>
                <th style="text-align:right;">SL Dư</th>
                <th style="text-align:left;">Đánh Giá</th>
            </tr></thead><tbody>`;
            recs.forEach((r, idx) => {
                bodyHtml += `<tr>
                    <td style="text-align:center;">${idx + 1}</td>
                    <td style="text-align:center; font-weight:700;">${escapeHtml(r.date)}</td>
                    <td style="text-align:right;">${fmtNum(r.pt_cnt)}</td>
                    <td style="text-align:right;">${fmtNum(r.sl_chuyen)}</td>
                    <td style="text-align:right;">${fmtNum(r.sl_nhan)}</td>
                    <td style="text-align:right;">${fmtNum(r.cdc_blank0)}</td>
                    <td style="text-align:right;">${fmtNum(r.cdc_blank_m1)}</td>
                    <td style="text-align:right;">${fmtNum(r.seedlog)}</td>
                    <td style="text-align:right;">${fmtNum(r.sl_du)}</td>
                    <td style="text-align:left;">${escapeHtml(r.status_txt)}</td>
                </tr>`;
            });
            bodyHtml += `</tbody></table>`;
        } else if (targetView === 'progress') {
            const pRows = getProgDailyRows();
            bodyHtml += `<table class="logic-tbl"><thead><tr>
                <th style="text-align:left;">Thời Gian</th>
                <th style="text-align:right;">SL Chuyển</th>
                <th style="text-align:right;">SL Nhận</th>
                <th style="text-align:right;">SL Lệch</th>
                <th style="text-align:right;">Tổng Tiền Lệch</th>
                <th style="text-align:center;">ST Lệch</th>
                <th style="text-align:right;">Trả DC (VNĐ)</th>
                <th style="text-align:right;">Trả ST (VNĐ)</th>
                <th style="text-align:right;">Write-OFF (VNĐ)</th>
                <th style="text-align:right;">Đã XL (VNĐ)</th>
                <th style="text-align:right;">Chưa XL (VNĐ)</th>
                <th style="text-align:center;">Tiến Độ</th>
            </tr></thead><tbody>`;
            pRows.forEach(r => {
                bodyHtml += `<tr>
                    <td style="font-weight:700;">${escapeHtml(r.date)}</td>
                    <td style="text-align:right;">${progFmtN(r.qty_chuyen)}</td>
                    <td style="text-align:right;">${progFmtN(r.qty_nhan)}</td>
                    <td style="text-align:right; color:#b91c1c; font-weight:700;">${progFmtN(r.qty_lech)}</td>
                    <td style="text-align:right; font-weight:700;">${progFmtVND(r.val_total)}</td>
                    <td style="text-align:center;">${progFmtN(r.st_lech)} ST</td>
                    <td style="text-align:right;">${progFmtVND(r.val_dc)}</td>
                    <td style="text-align:right;">${progFmtVND(r.val_st)}</td>
                    <td style="text-align:right;">${progFmtVND(r.val_wo)}</td>
                    <td style="text-align:right; color:#047857; font-weight:700;">${progFmtVND(r.val_da_xl)}</td>
                    <td style="text-align:right; color:#c2410c; font-weight:700;">${progFmtVND(r.val_cc)}</td>
                    <td style="text-align:center; font-weight:700;">${r.pct_val.toFixed(1)}%</td>
                </tr>`;
            });
            bodyHtml += `</tbody></table>`;
        }

        const win = window.open('', '_blank');
        if (!win) {
            alert('Trình duyệt đang chặn cửa sổ bật lên (Popup). Vui lòng cho phép Popup cho trang này rồi bấm Tải PDF lại.');
            return;
        }
        const isWide = (targetView === 'matrix' || (targetView === 'flow' && !flowSummaryOnly));
        win.document.write(`<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>${escapeHtml(docTitle)}</title>
<style>
    @page { size: A4 landscape; margin: 7mm; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; background: #fff; margin: 0; padding: 12px; font-size: ${isWide ? '7.2px' : '9px'}; }
    .no-print { display: flex; justify-content: space-between; align-items: center; background: #0f172a; color: #fff; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; }
    .no-print button { background: #e11d48; color: #fff; border: none; border-radius: 6px; padding: 7px 14px; font-weight: 700; cursor: pointer; font-size: 13px; }
    .hdr { border-bottom: 2px solid #1e3a8a; padding-bottom: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }
    .hdr h1 { margin: 0; font-size: 14px; color: #1e3a8a; }
    .hdr .sub { font-size: 9px; color: #475569; margin-top: 2px; }
    .kpis { display: flex; gap: 10px; margin-bottom: 8px; }
    .kpi { border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 10px; background: #f8fafc; flex: 1; }
    .kpi .kl { font-size: 8px; color: #64748b; text-transform: uppercase; font-weight: 700; }
    .kpi .kv { font-size: 11px; font-weight: 800; color: #0f172a; margin-top: 2px; }
    h3 { margin: 12px 0 5px 0; font-size: 11px; color: #1e3a8a; }
    table { width: 100%; border-collapse: collapse; table-layout: auto; }
    thead { display: table-header-group; }
    tr { page-break-inside: avoid; break-inside: avoid; }
    th, td { border: 1px solid #cbd5e1; padding: ${isWide ? '2.5px 3px' : '4px 5px'}; vertical-align: top; }
    th { background: #1e293b; color: #fff; font-weight: 700; white-space: nowrap; }
    .logic-tbl th, .logic-tbl td { white-space: normal; word-break: break-word; line-height: 1.35; }
    tr.sec-row td { background: #dbeafe; color: #1e3a8a; font-weight: 800; text-align: left; padding: 4px 6px; }
    tbody tr:nth-child(even) td { background: #f8fafc; }
    @media print {
        body { padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        .no-print { display: none !important; }
    }
</style>
</head>
<body>
    <div class="no-print">
        <div><strong>Xuất PDF Báo Cáo FMCG</strong> — Trong hộp thoại In, chọn Đích (Destination): <strong>Save as PDF / Lưu dưới dạng PDF</strong> (khổ ngang Landscape).</div>
        <button onclick="window.print()">Lưu thành PDF / In ngay</button>
    </div>
    <div class="hdr">
        <div>
            <h1>${escapeHtml(title)}</h1>
            <div class="sub">Nguồn: CDC StarRocks (Kho FGA10101 • User hệ thống TKE_WMS • Chỉ Siêu thị KFM) + Google Sheet Seedlog • Cập nhật: ${escapeHtml(currentData.updated_at || '')}</div>
        </div>
        <div class="sub" style="text-align:right;">Kỳ dữ liệu: 01/11 → ${escapeHtml(s.latest_cdc_date || s.latest_date || '')}</div>
    </div>
    <div class="kpis">
        <div class="kpi"><div class="kl">Tổng Chuyển Lũy Kế</div><div class="kv">${escapeHtml(fmtVndClean(s.tong_luy_ke))} VNĐ</div></div>
        <div class="kpi"><div class="kl">Tồn Kho Chênh Lệch</div><div class="kv">${escapeHtml(fmtVndClean(s.ton_kho_chenh_lech))} VNĐ</div></div>
        <div class="kpi"><div class="kl">Tỷ Lệ Lệch Chuyển Hàng</div><div class="kv">${escapeHtml(s.ty_le_chenh_lech || '0.00%')}</div></div>
    </div>
    ${bodyHtml}
    <script>setTimeout(function(){ window.focus(); window.print(); }, 350);</script>
</body>
</html>`);
        win.document.close();
    };

    // Helpers
    function updateStatusText(htmlStr) {
        const el = document.getElementById('fmcg-status-text');
        if (el) el.innerHTML = htmlStr;
    }

    function fmtNum(v) {
        if (v === null || v === undefined || isNaN(v)) return '-';
        if (Math.abs(v - Math.round(v)) < 0.005) return Math.round(v).toLocaleString('en-US');
        return Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function formatInlineCode(s) {
        return escapeHtml(s)
            .replace(/`([^`]+)`/g, '<code style="background:rgba(56,189,248,0.12); color:#7dd3fc; padding:1px 5px; border-radius:4px; font-family:\'JetBrains Mono\', monospace; font-size:0.74rem; word-break:break-all;">$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong style="color:#f8fafc;">$1</strong>');
    }

    function formatMetricTitle(name) {
        if (name.includes('chênh lệch') || name.includes('thất thoát')) return `<span style="color:#fca5a5;">${name}</span>`;
        if (name.includes('trả DC') || name.includes('xác nhận') || name.includes('DC chịu')) return `<span style="color:#7dd3fc;">${name}</span>`;
        if (name.includes('lũy kế') || name.includes('Tồn kho')) return `<strong style="color:#34d399;">${name}</strong>`;
        return name;
    }

    function formatCellValue(val, metricName) {
        if (!val || val === '#DIV/0!' || val === '#N/A' || val === '-') return `<span style="color:#475569;">-</span>`;
        const isPercent = val.includes('%');
        const isNegative = val.startsWith('-');
        if (isPercent) {
            if (val === '0.00%' || val === '0%') return `<span style="color:#64748b;">0.00%</span>`;
            return isNegative
                ? `<span style="color:#f87171; font-weight:700;">${val}</span>`
                : `<span style="color:#38bdf8; font-weight:600;">${val}</span>`;
        }
        if (isNegative) return `<span style="color:#f87171; font-weight:700; background:rgba(244,63,94,0.12); padding:1px 5px; border-radius:4px;">${val}</span>`;
        if (val === '0') return `<span style="color:#475569;">0</span>`;
        if (metricName.includes('Tổng giá trị') || metricName.includes('Tồn kho')) return `<strong style="color:#34d399;">${val}</strong>`;
        return `<span style="color:#f1f5f9;">${val}</span>`;
    }

    function getDayOfWeek(isoDate) {
        try {
            const d = new Date(isoDate);
            return ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'][d.getDay()] || '';
        } catch (e) { return ''; }
    }

    function isDateCurrent(isoDate) {
        return isoDate === new Date().toISOString().slice(0, 10);
    }

    window.toggleFmcgSort = function () {
        sortDescending = !sortDescending;
        const btn = document.getElementById('btn-fmcg-sort');
        if (btn) {
            btn.innerHTML = sortDescending
                ? `<i class="fa-solid fa-arrow-down-wide-short"></i> Ngày Mới Nhất Trước`
                : `<i class="fa-solid fa-arrow-up-wide-short"></i> Ngày Cũ Nhất Trước`;
        }
        renderActiveSubView();
    };

    window.filterFmcgSection = function (secId) {
        filterSection = secId;
        document.querySelectorAll('.fmcg-sec-pill').forEach(b => {
            if (b.getAttribute('data-sec') === secId) {
                b.style.background = '#0369a1';
                b.style.borderColor = 'rgba(56,189,248,0.5)';
                b.style.color = '#ffffff';
            } else {
                b.style.background = '#28354a';
                b.style.borderColor = 'rgba(255,255,255,0.1)';
                b.style.color = '#cbd5e1';
            }
        });
        renderActiveSubView();
    };

    window.searchFmcgMetrics = function (input) {
        searchQuery = input.value || '';
        renderActiveSubView();
    };

    // =========================================================================
    // VIEW 5: THEO DÕI TIẾN ĐỘ & XẾP HẠNG SIÊU THỊ (CHUẨN GIAO DIỆN TAB 2 — KHÔNG NGƯỠNG 100K, KHÔNG HAO HỤT)
    // =========================================================================
    let progSubTab = 1;
    let progPeriod = 'daily';

    function getProgDailyRows() {
        if (!currentData || !currentData.dates || !currentData.sections) return [];
        const metricMap = {};
        currentData.sections.forEach(sec => {
            (sec.rows || []).forEach(r => { metricMap[(r.name || '').trim()] = r.values || {}; });
        });
        // Tính số ST Đã XL / Chưa XL từng ngày từ window.FMCG_STORE_DETAILS (khớp chuẩn logic đếm ST của Tab 2)
        const stStatsByIso = {};
        const det = window.FMCG_STORE_DETAILS || { store_ranking: [] };
        (det.store_ranking || []).forEach(s => {
            const iso = s.iso_date || '';
            if (!iso) return;
            if (!stStatsByIso[iso]) stStatsByIso[iso] = { st_da_xl: 0, st_chua_xl: 0 };
            if ((s.val_da_xl || 0) > 0) stStatsByIso[iso].st_da_xl++;
            if ((s.val_chua_xl || 0) > 0) stStatsByIso[iso].st_chua_xl++;
        });

        const num = (name, iso) => {
            const v = metricMap[name] ? metricMap[name][iso] : 0;
            if (v === null || v === undefined || v === '') return 0;
            const n = parseFloat(String(v).replace(/,/g, '').replace(/%/g, '').trim());
            return isNaN(n) ? 0 : n;
        };
        const getIso = d => (d && (d.iso || d.iso_date)) ? String(d.iso || d.iso_date) : '';
        const getDisp = d => (d && (d.display || d.display_date || d.iso || d.iso_date)) ? String(d.display || d.display_date || d.iso || d.iso_date) : '';
        const dates = [...currentData.dates].sort((a, b) => sortDescending ? getIso(b).localeCompare(getIso(a)) : getIso(a).localeCompare(getIso(b)));
        return dates.map(d => {
            const iso = getIso(d);
            const parts = iso.split('-');
            const month = parts.length === 3 ? `Tháng ${parseInt(parts[1], 10)}/${parts[0]}` : '';
            const qty_chuyen = num('SL chuyển', iso), qty_nhan = num('SL nhận', iso);
            const qty_lech = Math.abs(num('SL chênh lệch', iso)), val_total = Math.abs(num('Giá trị chênh lệch', iso));
            const st_lech = num('SL ST chênh lệch', iso);
            const sl_dc = Math.abs(num('SL trả DC', iso)), val_dc = Math.abs(num('Giá trị trả DC', iso));
            const sl_st = Math.abs(num('SL trả ST', iso)), val_st = Math.abs(num('Giá trị trả ST', iso));
            const sl_wo = Math.abs(num('SL Write - OFF', iso)), val_wo = Math.abs(num('Giá trị Write - OFF', iso));
            const sl_cc = Math.abs(num('SL SCM chưa check', iso)), val_cc = Math.abs(num('Giá trị SCM chưa check', iso));
            const sl_da_xl = sl_dc + sl_st + sl_wo, val_da_xl = val_dc + val_st + val_wo;
            const pct_val = val_total > 0 ? +(Math.min(val_da_xl / val_total, 1) * 100).toFixed(1) : (qty_lech === 0 ? 100 : 0);
            const pct_sl = qty_lech > 0 ? +(Math.min(sl_da_xl / qty_lech, 1) * 100).toFixed(1) : (qty_lech === 0 ? 100 : 0);
            const stInfo = stStatsByIso[iso] || { st_da_xl: 0, st_chua_xl: 0 };
            return {
                iso, date: getDisp(d), month,
                qty_chuyen, qty_nhan, qty_lech, val_total, st_lech,
                st_da_xl: stInfo.st_da_xl, st_chua_xl: stInfo.st_chua_xl,
                sl_dc, val_dc, sl_st, val_st, sl_wo, val_wo, sl_cc, val_cc,
                sl_da_xl, val_da_xl, pct_val, pct_sl
            };
        });
    }

    function progFmtN(n) { return new Intl.NumberFormat('vi-VN').format(Math.round((n || 0) * 100) / 100); }
    function progFmtVND(n) { return new Intl.NumberFormat('vi-VN').format(Math.round(n || 0)) + ' đ'; }
    function progBadgePct(pct) {
        if (typeof window.renderProgressBadge === 'function') {
            return window.renderProgressBadge(pct);
        }
        const num = parseFloat(pct) || 0;
        let color = '#34d399', bg = 'linear-gradient(90deg,#059669,#34d399)';
        if (num < 70) { color = '#f87171'; bg = 'linear-gradient(90deg,#b91c1c,#f87171)'; }
        else if (num < 90) { color = '#fbbf24'; bg = 'linear-gradient(90deg,#d97706,#fbbf24)'; }
        return `<div style="display:flex;align-items:center;gap:6px;justify-content:center;"><div style="width:62px;height:6px;background:rgba(255,255,255,0.1);border-radius:999px;overflow:hidden;"><div style="width:${Math.min(num,100)}%;height:100%;background:${bg};border-radius:999px;"></div></div><span style="color:${color};font-weight:700;font-size:0.78rem;min-width:44px;text-align:right;">${num.toFixed(1)}%</span></div>`;
    }

    function renderProgressView() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;
        const dailyRows = getProgDailyRows();
        const sumKeys = ['qty_chuyen','qty_nhan','qty_lech','val_total','st_lech','st_da_xl','st_chua_xl','sl_dc','val_dc','sl_st','val_st','sl_wo','val_wo','sl_cc','val_cc','sl_da_xl','val_da_xl'];
        let rows = dailyRows;
        if (progPeriod === 'monthly') {
            const map = {};
            dailyRows.forEach(r => {
                if (!map[r.month]) {
                    map[r.month] = { iso: r.month, date: r.month };
                    sumKeys.forEach(k => map[r.month][k] = 0);
                }
                const m = map[r.month];
                sumKeys.forEach(k => m[k] += (r[k] || 0));
            });
            rows = Object.values(map).map(m => ({
                ...m,
                pct_val: m.val_total > 0 ? +(Math.min(m.val_da_xl / m.val_total, 1) * 100).toFixed(1) : 100,
                pct_sl: m.qty_lech > 0 ? +(Math.min(m.sl_da_xl / m.qty_lech, 1) * 100).toFixed(1) : 100
            }));
        }
        const tot = rows.reduce((a, r) => { sumKeys.forEach(k => a[k] = (a[k] || 0) + (r[k] || 0)); return a; }, {});
        tot.pct_val = tot.val_total > 0 ? +(Math.min(tot.val_da_xl / tot.val_total, 1) * 100).toFixed(1) : 100;
        tot.pct_sl = tot.qty_lech > 0 ? +(Math.min(tot.sl_da_xl / tot.qty_lech, 1) * 100).toFixed(1) : 100;

        const subDefs = [
            { id: 1, icon: 'fa-layer-group', title: 'BẢNG TỔNG HỢP TIẾN ĐỘ', sub: 'Hợp nhất SL & Giá trị theo ngày/tháng' },
            { id: 2, icon: 'fa-money-bill-trend-up', title: 'BẢNG GIÁ TRỊ (VNĐ)', sub: 'Bóc tách dòng tiền Trả DC / ST / Write-OFF' },
            { id: 3, icon: 'fa-boxes-stacked', title: 'BẢNG SỐ LƯỢNG (PCS)', sub: 'Số lượng giao nhận & Điểm nhận' },
            { id: 4, icon: 'fa-triangle-exclamation', title: 'DS SIÊU THỊ CHÊNH LỆCH (CAO → THẤP)', sub: 'Xếp hạng ưu tiên xử lý & Xem từng SKU' }
        ];
        const subBtns = subDefs.map(b => {
            const act = progSubTab === b.id;
            return `<button class="sub-tab-btn${act ? ' active active-sub-' + b.id : ''}" onclick="switchFmcgProgTab(${b.id})">
                <span class="tab-badge-num">${b.id}</span>
                <span class="tab-btn-text"><i class="fa-solid ${b.icon}"></i> ${b.title}</span>
                <span class="tab-btn-sub">${b.sub}</span>
            </button>`;
        }).join('');

        const periodSwitch = `<div class="seg-pill">
            <button class="seg-btn${progPeriod === 'daily' ? ' active' : ''}" onclick="setFmcgProgPeriod('daily')">Theo Ngày</button>
            <button class="seg-btn${progPeriod === 'monthly' ? ' active' : ''}" onclick="setFmcgProgPeriod('monthly')">Theo Tháng</button>
        </div>`;

        const btnViewDay = (iso, dVn) => `<button class="btn-view-detail" onclick="openFmcgDetailModal('${iso}','${dVn}','')"><i class="fa-solid fa-list-ul"></i> Xem</button>`;
        const footUnitLabel = progPeriod === 'daily' ? `${rows.length} Ngày` : `${rows.length} Tháng`;

        let cardHtml = '';
        if (progSubTab === 1) {
            // BẢNG 1: BẢNG TỔNG HỢP TIẾN ĐỘ (GIỐNG TAB 2.1 — KHÔNG NGƯỠNG 100K, KHÔNG HAO HỤT)
            cardHtml = `
            <div class="table-card">
                <div class="table-header-row">
                    <div class="table-title">
                        <i class="fa-solid fa-layer-group" style="color:#38bdf8;"></i> BẢNG TỔNG HỢP TIẾN ĐỘ (FMCG)
                    </div>
                    ${periodSwitch}
                </div>
                <div class="table-responsive">
                    <table class="sc-table">
                        <thead>
                            <tr>
                                <th rowspan="2" class="th-master-bg" style="width:105px;">Thời Gian</th>
                                <th colspan="2" class="th-master-bg">Giao Nhận</th>
                                <th rowspan="2" class="th-master-bg" style="background:#0369a1 !important; color:#fff;">Chênh Lệch<br><span style="font-size:0.7rem; font-weight:400; opacity:0.9;">(SL &amp; Tiền VNĐ)</span></th>
                                <th rowspan="2" class="th-master-bg">Số ST Lệch</th>
                                <th colspan="3" class="th-master-bg">Điểm Nhận Trách Nhiệm</th>
                                <th colspan="3" class="th-master-bg">Tiến Độ Xử Lý</th>
                                <th rowspan="2" class="th-master-bg" style="width:75px;">Chi Tiết</th>
                            </tr>
                            <tr>
                                <th class="th-master-sub">SL Chuyển</th>
                                <th class="th-master-sub">SL Nhận</th>
                                <th class="th-master-sub">Kho DC (Trả DC)</th>
                                <th class="th-master-sub">Siêu Thị (Trả ST)</th>
                                <th class="th-master-sub">Write - OFF</th>
                                <th class="th-master-sub">🟢 Đã XL</th>
                                <th class="th-master-sub" style="color:#fed7aa;">🟡 Chưa XL</th>
                                <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(r => `<tr>
                                <td class="text-left" style="font-weight:600; color:var(--primary);">${r.date}</td>
                                <td>${progFmtN(r.qty_chuyen)}</td>
                                <td>${progFmtN(r.qty_nhan)}</td>
                                <td>
                                    <div class="c-red" style="font-weight:700;">${progFmtN(r.qty_lech)}</div>
                                    <div class="c-blue" style="font-size:0.75rem;">${progFmtVND(r.val_total)}</div>
                                </td>
                                <td class="text-center"><strong>${progFmtN(r.st_lech)} ST</strong></td>
                                <td>
                                    <div>${progFmtN(r.sl_dc)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(r.val_dc)}</div>
                                </td>
                                <td>
                                    <div>${progFmtN(r.sl_st)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(r.val_st)}</div>
                                </td>
                                <td>
                                    <div>${progFmtN(r.sl_wo)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(r.val_wo)}</div>
                                </td>
                                <td>
                                    <div class="c-green" style="font-weight:700;">${progFmtN(r.sl_da_xl)}</div>
                                    <div style="font-size:0.75rem; color:#34d399;">${progFmtVND(r.val_da_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_da_xl)} ST)</span></div>
                                </td>
                                <td>
                                    <div class="c-orange" style="font-weight:700;">${progFmtN(r.sl_cc)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_chua_xl)} ST)</span></div>
                                    <div style="font-size:0.75rem; color:#fb923c;">${progFmtVND(r.val_cc)}</div>
                                </td>
                                <td class="text-center">${progBadgePct(r.pct_val)}</td>
                                <td class="text-center">${progPeriod === 'daily' && r.qty_lech > 0 ? btnViewDay(r.iso, r.date) : '-'}</td>
                            </tr>`).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td class="text-left">TỔNG CỘNG</td>
                                <td>${progFmtN(tot.qty_chuyen)}</td>
                                <td>${progFmtN(tot.qty_nhan)}</td>
                                <td>
                                    <div class="c-red" style="font-weight:700;">${progFmtN(tot.qty_lech)}</div>
                                    <div class="c-blue" style="font-size:0.75rem;">${progFmtVND(tot.val_total)}</div>
                                </td>
                                <td class="text-center"><strong>${progFmtN(tot.st_lech)} ST</strong></td>
                                <td>
                                    <div>${progFmtN(tot.sl_dc)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(tot.val_dc)}</div>
                                </td>
                                <td>
                                    <div>${progFmtN(tot.sl_st)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(tot.val_st)}</div>
                                </td>
                                <td>
                                    <div>${progFmtN(tot.sl_wo)}</div>
                                    <div style="font-size:0.75rem; color:var(--text-muted);">${progFmtVND(tot.val_wo)}</div>
                                </td>
                                <td>
                                    <div class="c-green"><strong>${progFmtN(tot.sl_da_xl)}</strong></div>
                                    <div style="font-size:0.75rem; color:#34d399;">${progFmtVND(tot.val_da_xl)} <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_da_xl)} lần giao)</span></div>
                                </td>
                                <td>
                                    <div class="c-orange"><strong>${progFmtN(tot.sl_cc)}</strong> <span style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_chua_xl)} lần giao)</span></div>
                                    <div style="font-size:0.75rem; color:#fb923c;">${progFmtVND(tot.val_cc)}</div>
                                </td>
                                <td class="text-center">${progBadgePct(tot.pct_val)}</td>
                                <td class="text-center">${footUnitLabel}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>`;
        } else if (progSubTab === 2) {
            // BẢNG 2: BẢNG GIÁ TRỊ (VNĐ) (GIỐNG TAB 2.2)
            cardHtml = `
            <div class="table-card">
                <div class="table-header-row">
                    <div class="table-title">
                        <i class="fa-solid fa-money-bill-wave" style="color:#38bdf8;"></i> BẢNG GIÁ TRỊ (VNĐ)
                    </div>
                    ${periodSwitch}
                </div>
                <div class="table-responsive">
                    <table class="sc-table">
                        <thead>
                            <tr>
                                <th rowspan="2" class="th-val-bg" style="width:110px;">Thời Gian</th>
                                <th rowspan="2" class="th-val-bg">Tổng Tiền Lệch</th>
                                <th colspan="3" class="th-val-bg">Điểm Nhận Trách Nhiệm (VNĐ)</th>
                                <th colspan="3" class="th-val-bg">Tiến Độ Xử Lý (VNĐ)</th>
                                <th rowspan="2" class="th-val-bg" style="width:80px;">Chi Tiết</th>
                            </tr>
                            <tr>
                                <th class="th-val-sub">Kho DC (Trả DC)</th>
                                <th class="th-val-sub">Siêu Thị (Trả ST)</th>
                                <th class="th-val-sub">Write - OFF</th>
                                <th class="th-val-sub">🟢 Đã Xử Lý</th>
                                <th class="th-val-sub" style="color:#fed7aa;">🟡 Chưa Xử Lý</th>
                                <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(r => `<tr>
                                <td class="text-left" style="font-weight:600; color:var(--primary);">${r.date}</td>
                                <td class="c-blue"><strong>${progFmtVND(r.val_total)}</strong></td>
                                <td>${progFmtVND(r.val_dc)}</td>
                                <td>${progFmtVND(r.val_st)}</td>
                                <td>${progFmtVND(r.val_wo)}</td>
                                <td>
                                    <div class="c-green">${progFmtVND(r.val_da_xl)}</div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_da_xl)} ST)</div>
                                </td>
                                <td>
                                    <div class="c-orange">${progFmtVND(r.val_cc)}</div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_chua_xl)} ST)</div>
                                </td>
                                <td class="text-center">${progBadgePct(r.pct_val)}</td>
                                <td class="text-center">${progPeriod === 'daily' && r.qty_lech > 0 ? btnViewDay(r.iso, r.date) : '-'}</td>
                            </tr>`).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td class="text-left">TỔNG CỘNG</td>
                                <td class="c-blue"><strong>${progFmtVND(tot.val_total)}</strong></td>
                                <td>${progFmtVND(tot.val_dc)}</td>
                                <td>${progFmtVND(tot.val_st)}</td>
                                <td>${progFmtVND(tot.val_wo)}</td>
                                <td>
                                    <div class="c-green"><strong>${progFmtVND(tot.val_da_xl)}</strong></div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_da_xl)} lần giao)</div>
                                </td>
                                <td>
                                    <div class="c-orange"><strong>${progFmtVND(tot.val_cc)}</strong></div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_chua_xl)} lần giao)</div>
                                </td>
                                <td class="text-center">${progBadgePct(tot.pct_val)}</td>
                                <td class="text-center">${footUnitLabel}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>`;
        } else if (progSubTab === 3) {
            // BẢNG 3: BẢNG SỐ LƯỢNG (PCS) (GIỐNG TAB 2.3)
            cardHtml = `
            <div class="table-card">
                <div class="table-header-row">
                    <div class="table-title">
                        <i class="fa-solid fa-boxes-packing" style="color:#818cf8;"></i> BẢNG SỐ LƯỢNG (PCS)
                    </div>
                    ${periodSwitch}
                </div>
                <div class="table-responsive">
                    <table class="sc-table">
                        <thead>
                            <tr>
                                <th rowspan="2" class="th-qty-bg" style="width:110px;">Thời Gian</th>
                                <th colspan="3" class="th-qty-bg">Giao Nhận (SL Hàng)</th>
                                <th colspan="3" class="th-qty-bg">Số Siêu Thị Lệch (ST)</th>
                                <th colspan="3" class="th-qty-bg">Điểm Nhận (SL Hàng)</th>
                                <th colspan="3" class="th-qty-bg">Tiến Độ Xử Lý (SL Hàng)</th>
                                <th rowspan="2" class="th-qty-bg" style="width:80px;">Chi Tiết</th>
                            </tr>
                            <tr>
                                <th class="th-qty-sub">SL Chuyển</th>
                                <th class="th-qty-sub">SL Nhận</th>
                                <th class="th-qty-sub">SL Lệch</th>
                                <th class="th-qty-sub">Tổng ST</th>
                                <th class="th-qty-sub">🟢 ST Đã XL</th>
                                <th class="th-qty-sub">🟡 ST Chưa XL</th>
                                <th class="th-qty-sub">Kho DC (Trả DC)</th>
                                <th class="th-qty-sub">Siêu Thị (Trả ST)</th>
                                <th class="th-qty-sub">Write - OFF</th>
                                <th class="th-qty-sub">🟢 Đã Xử Lý</th>
                                <th class="th-qty-sub" style="color:#fed7aa;">🟡 Chưa Xử Lý</th>
                                <th class="th-master-sub" style="width:130px; text-align:center;">Tiến Độ (% Xong)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(r => `<tr>
                                <td class="text-left" style="font-weight:600; color:var(--primary);">${r.date}</td>
                                <td>${progFmtN(r.qty_chuyen)}</td>
                                <td>${progFmtN(r.qty_nhan)}</td>
                                <td class="c-red"><strong>${progFmtN(r.qty_lech)}</strong></td>
                                <td>${progFmtN(r.st_lech)} ST</td>
                                <td class="c-green">${progFmtN(r.st_da_xl)} ST</td>
                                <td class="c-orange">${progFmtN(r.st_chua_xl)} ST</td>
                                <td>${progFmtN(r.sl_dc)}</td>
                                <td>${progFmtN(r.sl_st)}</td>
                                <td>${progFmtN(r.sl_wo)}</td>
                                <td>
                                    <div class="c-green">${progFmtN(r.sl_da_xl)}</div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_da_xl)} ST)</div>
                                </td>
                                <td>
                                    <div class="c-orange">${progFmtN(r.sl_cc)}</div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(r.st_chua_xl)} ST)</div>
                                </td>
                                <td class="text-center">${progBadgePct(r.pct_sl)}</td>
                                <td class="text-center">${progPeriod === 'daily' && r.qty_lech > 0 ? btnViewDay(r.iso, r.date) : '-'}</td>
                            </tr>`).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td class="text-left">TỔNG CỘNG</td>
                                <td>${progFmtN(tot.qty_chuyen)}</td>
                                <td>${progFmtN(tot.qty_nhan)}</td>
                                <td class="c-red"><strong>${progFmtN(tot.qty_lech)}</strong></td>
                                <td>${progFmtN(tot.st_lech)} ST</td>
                                <td class="c-green"><strong>${progFmtN(tot.st_da_xl)} ST</strong></td>
                                <td class="c-orange"><strong>${progFmtN(tot.st_chua_xl)} ST</strong></td>
                                <td>${progFmtN(tot.sl_dc)}</td>
                                <td>${progFmtN(tot.sl_st)}</td>
                                <td>${progFmtN(tot.sl_wo)}</td>
                                <td>
                                    <div class="c-green"><strong>${progFmtN(tot.sl_da_xl)}</strong></div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_da_xl)} lần giao)</div>
                                </td>
                                <td>
                                    <div class="c-orange"><strong>${progFmtN(tot.sl_cc)}</strong></div>
                                    <div style="font-size:0.72rem; color:var(--text-muted); font-weight:400;">(${progFmtN(tot.st_chua_xl)} lần giao)</div>
                                </td>
                                <td class="text-center">${progBadgePct(tot.pct_sl)}</td>
                                <td class="text-center">${footUnitLabel}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>`;
        } else {
            // BẢNG 4: DANH SÁCH SIÊU THỊ CẦN XỬ LÝ FMCG (GIỐNG TAB 2.4 — XẾP HẠNG CAO -> THẤP, KHÔNG NGƯỠNG 100K)
            const det = window.FMCG_STORE_DETAILS || { store_ranking: [] };
            const allSt = det.store_ranking || [];
            const datesOpt = [...new Set(allSt.map(s => s.date))].sort((a, b) => {
                const pa = a.split('/').reverse().join('');
                const pb = b.split('/').reverse().join('');
                return pb.localeCompare(pa);
            });
            cardHtml = `
            <div class="table-card" style="border-top: 3px solid #ef4444;">
                <div class="table-header-row">
                    <div class="table-title" style="color:#f87171; font-size:1.1rem;">
                        <i class="fa-solid fa-triangle-exclamation" style="color:#f87171;"></i> DANH SÁCH SIÊU THỊ CẦN XỬ LÝ FMCG (ƯU TIÊN THEO CHƯA XL / NGÀY)
                    </div>
                    <button class="btn-view-detail" style="background:#10b981; color:#fff; border-color:#059669; padding:0.35rem 0.85rem;" onclick="exportFmcgStoreRankingExcel()">
                        <i class="fa-solid fa-file-excel"></i> Xuất Excel DS Siêu Thị
                    </button>
                </div>
                <div class="fmcg-st-toolbar" style="padding:0.65rem 0.85rem; background:var(--bg-card-alt); border-radius:10px; margin-bottom:0.85rem; border:1px solid var(--border-card); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.65rem;">
                    <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                        <input id="fmcg-st-search" type="text" placeholder="🔍 Tìm mã ST, tên siêu thị..." oninput="filterFmcgStoreRanking()" style="padding:0.4rem 0.75rem; border-radius:6px; font-size:0.82rem; width:260px; outline:none;">
                        <select id="fmcg-st-date" onchange="filterFmcgStoreRanking()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">📅 Tất cả các ngày (${datesOpt.length} ngày)</option>
                            ${datesOpt.map(d => `<option value="${d}">${d}</option>`).join('')}
                        </select>
                        <select id="fmcg-st-status" onchange="filterFmcgStoreRanking()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="all">🎯 Tất cả trạng thái</option>
                            <option value="pending">🚨 Cần xử lý (Còn Chưa XL)</option>
                            <option value="done">🟢 Đã xử lý hoàn tất (100%)</option>
                        </select>
                        <select id="fmcg-st-sort" onchange="filterFmcgStoreRanking()" style="padding:0.4rem 0.65rem; border-radius:6px; font-size:0.82rem; font-weight:600;">
                            <option value="chua_xl_desc">🟡 Tiền Chưa XL giảm dần (Ưu tiên)</option>
                            <option value="val_desc">💰 Tổng tiền lệch ST giảm dần</option>
                            <option value="sku_desc">📦 Số lượng SKU lệch nhiều nhất</option>
                        </select>
                    </div>
                    <div id="fmcg-st-summary" style="font-size:0.82rem; font-weight:600; color:var(--text-secondary);"></div>
                </div>
                <div class="table-responsive">
                    <table class="sc-table" id="fmcgStorePriorityTable">
                        <thead>
                            <tr>
                                <th class="th-store-bg text-center" style="width:45px;">STT</th>
                                <th class="th-store-bg text-center" style="width:90px;">Ngày</th>
                                <th class="th-store-bg text-left" style="width:27%;">Siêu Thị Cần Xử Lý</th>
                                <th class="th-store-bg text-center" style="width:14%;">Trạng Thái</th>
                                <th class="th-store-bg" style="width:12%;">Tổng Tiền Lệch / ST</th>
                                <th class="th-store-bg text-center" style="width:7%;">Số SKU</th>
                                <th class="th-store-bg" style="width:12%; color:#fed7aa;">🟡 Chưa XL (Ưu tiên)</th>
                                <th class="th-store-bg" style="width:11%; color:#bbf7d0;">🟢 Đã XL</th>
                                <th class="th-store-bg text-center" style="width:130px;">Tiến Độ (% Xong)</th>
                                <th class="th-store-bg text-center" style="width:85px;">Chi Tiết</th>
                            </tr>
                        </thead>
                        <tbody id="fmcg-st-tbody"></tbody>
                        <tfoot id="fmcg-st-tfoot"></tfoot>
                    </table>
                </div>
            </div>`;
        }

        container.innerHTML = `
        <div class="fmcg-prog-wrap">
            <div class="section-panel-header">
                <div class="section-panel-title">
                    <i class="fa-solid fa-scale-unbalanced-flip" style="color:#238636;"></i> ĐỐI SOÁT CHÊNH LỆCH &amp; TIẾN ĐỘ XỬ LÝ FMCG
                    <span style="font-size:0.74rem; font-weight:600; color:var(--text-secondary); margin-left:6px;">(Chuẩn Tab 2 • Không ngưỡng 100K • Không hao hụt)</span>
                </div>
            </div>
            <div class="sub-tabs-bar">
                <div class="sub-tabs-header-label">
                    <i class="fa-solid fa-folder-tree"></i> CHỌN BẢNG DỮ LIỆU ĐỐI SOÁT FMCG XEM CHI TIẾT:
                </div>
                <div class="sub-tabs-list">
                    ${subBtns}
                </div>
            </div>
            ${cardHtml}
        </div>`;

        updateStatusText(`<strong>Bảng 5: Theo Dõi Tiến Độ &amp; Xếp Hạng ST (Chuẩn Tab 2 • FMCG)</strong> • Không ngưỡng 100K, không hao hụt • <strong>${dailyRows.length}</strong> ngày (01/11 → ${currentData.dates[currentData.dates.length - 1].display}) • Cập nhật: <strong>${currentData.updated_at || ''}</strong>`);
        if (progSubTab === 4) { window.filterFmcgStoreRanking(); }
    }

    window.switchFmcgProgTab = function (id) { progSubTab = id; renderActiveSubView(); };
    window.setFmcgProgPeriod = function (p) { progPeriod = p; renderActiveSubView(); };

    window.exportFmcgStoreRankingExcel = function () {
        if (!window.XLSX) { alert('Thư viện Excel chưa tải xong.'); return; }
        const tbl = document.getElementById('fmcgStorePriorityTable');
        if (!tbl) return;
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.table_to_sheet(tbl);
        XLSX.utils.book_append_sheet(wb, ws, 'DS_Sieu_Thi_FMCG');
        XLSX.writeFile(wb, `DS_Sieu_Thi_Can_Xu_Ly_FMCG_${new Date().toISOString().slice(0, 10)}.xlsx`);
    };

    window.filterFmcgStoreRanking = function () {
        const det = window.FMCG_STORE_DETAILS || { store_ranking: [] };
        const q = (document.getElementById('fmcg-st-search')?.value || '').trim().toLowerCase();
        const d = document.getElementById('fmcg-st-date')?.value || 'all';
        const st = document.getElementById('fmcg-st-status')?.value || 'all';
        const sortBy = document.getElementById('fmcg-st-sort')?.value || 'chua_xl_desc';
        let list = (det.store_ranking || []).filter(s => {
            if (d !== 'all' && s.date !== d) return false;
            if (st === 'pending' && s.val_chua_xl <= 0) return false;
            if (st === 'done' && s.val_chua_xl > 0) return false;
            if (q && !(s.st.toLowerCase().includes(q) || (s.store_name || '').toLowerCase().includes(q))) return false;
            return true;
        });
        list.sort((a, b) => {
            if (sortBy === 'val_desc') return b.val_total - a.val_total;
            if (sortBy === 'sku_desc') return b.sku_count - a.sku_count;
            if (b.val_chua_xl !== a.val_chua_xl) return b.val_chua_xl - a.val_chua_xl;
            return b.val_total - a.val_total;
        });
        const tbody = document.getElementById('fmcg-st-tbody');
        const tfoot = document.getElementById('fmcg-st-tfoot');
        const sumEl = document.getElementById('fmcg-st-summary');
        if (!tbody || !tfoot) return;

        const pendingList = list.filter(s => s.val_chua_xl > 0);
        const doneCount = list.length - pendingList.length;
        const tVal = list.reduce((a, s) => a + (s.val_total || 0), 0);
        const tSku = list.reduce((a, s) => a + (s.sku_count || 0), 0);
        const tChua = list.reduce((a, s) => a + (s.val_chua_xl || 0), 0);
        const tDa = list.reduce((a, s) => a + (s.val_da_xl || 0), 0);

        tbody.innerHTML = list.slice(0, 500).map((s, idx) => {
            const badge = s.val_chua_xl > 0
                ? '<span class="p-badge p-badge-p1">🚨 CẦN XỬ LÝ</span>'
                : '<span class="p-badge p-badge-p4">🟢 ĐÃ XONG 100%</span>';
            const tagFmcg = '<span class="tag-pill" style="background:rgba(56,189,248,0.16); color:#38bdf8; border:1px solid rgba(56,189,248,0.35);">FMCG</span>';
            return `<tr>
                <td class="text-center" style="color:var(--text-muted); font-weight:700;">#${idx + 1}</td>
                <td class="text-center" style="font-weight:600; color:var(--text-secondary);">${s.date}</td>
                <td class="text-left">
                    <strong style="color:var(--text-primary); font-size:0.85rem;">${s.st}</strong>${s.store_name ? ' - <span style="color:var(--text-secondary);">' + escapeHtml(s.store_name) + '</span>' : ''}
                    <div style="margin-top:2px; display:flex; gap:5px;">${tagFmcg}</div>
                </td>
                <td class="text-center">${badge}</td>
                <td><strong class="c-blue" style="font-size:0.88rem;">${progFmtVND(s.val_total)}</strong></td>
                <td class="text-center"><strong>${s.sku_count}</strong></td>
                <td><strong class="c-orange" style="font-size:0.85rem;">${s.val_chua_xl > 0 ? progFmtVND(s.val_chua_xl) : '-'}</strong></td>
                <td><strong class="c-green">${s.val_da_xl > 0 ? progFmtVND(s.val_da_xl) : '-'}</strong></td>
                <td class="text-center">${progBadgePct(s.pct_done)}</td>
                <td class="text-center">
                    <button class="btn-view-detail" onclick="openFmcgDetailModal('${s.iso_date}','${s.date}','${s.st}')">
                        <i class="fa-solid fa-magnifying-glass"></i> Xem SKU
                    </button>
                </td>
            </tr>`;
        }).join('') || `<tr><td colspan="10" class="text-center" style="padding:2rem;">Không tìm thấy siêu thị nào phù hợp bộ lọc</td></tr>`;

        const pctTot = tVal > 0 ? (tDa / tVal * 100) : 100;
        tfoot.innerHTML = `<tr>
            <td colspan="4" class="text-left"><strong>TỔNG CỘNG (${list.length} lượt ST${list.length > 500 ? ', đang hiện top 500' : ''})</strong></td>
            <td><strong class="c-blue">${progFmtVND(tVal)}</strong></td>
            <td class="text-center"><strong>${progFmtN(tSku)}</strong></td>
            <td><strong class="c-orange">${progFmtVND(tChua)}</strong></td>
            <td><strong class="c-green">${progFmtVND(tDa)}</strong></td>
            <td class="text-center">${progBadgePct(pctTot)}</td>
            <td class="text-center">-</td>
        </tr>`;
        if (sumEl) {
            sumEl.innerHTML = `<span>Hiển thị: <strong>${list.length}</strong> Siêu Thị • <span style="color:#fb923c; font-weight:700;">🟡 Cần XL: ${pendingList.length} ST (${progFmtVND(tChua)})</span> • 🟢 Xong: ${doneCount} ST</span>`;
        }
    };

    window.openFmcgDetailModal=function(isoDate,dateVn,stCode){
        const det=window.FMCG_STORE_DETAILS||{sku_by_date:{}};
        const items=(det.sku_by_date&&det.sku_by_date[isoDate])?det.sku_by_date[isoDate]:[];
        let modal=document.getElementById('fmcg-detail-modal');
        if(!modal){modal=document.createElement('div');modal.id='fmcg-detail-modal';modal.style.cssText='position:fixed;inset:0;background:rgba(2,6,23,0.8);z-index:99999;display:flex;align-items:center;justify-content:center;padding:18px;';modal.onclick=function(e){if(e.target===modal)modal.style.display='none';};document.body.appendChild(modal);}
        modal.style.display='flex';
        window._fmcgModalItems=stCode?items.filter(r=>r.st===stCode):items;
        modal.innerHTML=`<div style="background:#111827;border:1px solid rgba(56,189,248,0.35);border-radius:14px;width:100%;max-width:1280px;max-height:86vh;display:flex;flex-direction:column;overflow:hidden;color:#f1f5f9;"><div style="padding:13px 18px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,0.16);display:flex;justify-content:space-between;align-items:center;"><div style="font-weight:800;font-size:0.95rem;"><i class="fa-solid fa-list-check" style="color:#38bdf8;"></i> Chi Tiết SKU Chênh Lệch FMCG — Ngày ${dateVn}${stCode?' • ST '+stCode:''}</div><button onclick="document.getElementById('fmcg-detail-modal').style.display='none'" style="background:rgba(248,113,113,0.15);color:#f87171;border:1px solid rgba(248,113,113,0.35);border-radius:7px;padding:4px 10px;cursor:pointer;font-weight:700;">Đóng</button></div><div style="padding:10px 18px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,0.14);display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;"><div style="display:flex;flex-wrap:wrap;gap:8px;"><input id="fmcg-m-search" type="text" value="${stCode||''}" placeholder="Tìm ST, Mã PT, Barcode, Ghi chú..." oninput="renderFmcgModalRows()" style="background:#1e293b;border:1px solid rgba(148,163,184,0.25);color:#f1f5f9;padding:5px 10px;border-radius:7px;font-size:0.79rem;width:280px;"><select id="fmcg-m-status" onchange="renderFmcgModalRows()" style="background:#1e293b;border:1px solid rgba(148,163,184,0.25);color:#f1f5f9;padding:5px 10px;border-radius:7px;font-size:0.79rem;"><option value="all">Tất cả trạng thái</option><option value="Chưa XL">🟡 Chưa XL (SCM chưa check)</option><option value="Đã XL">🟢 Đã XL</option></select></div><div id="fmcg-m-sum" style="font-size:0.78rem;color:#94a3b8;"></div></div><div style="overflow:auto;flex:1;"><table style="width:100%;border-collapse:collapse;font-size:0.79rem;"><thead><tr style="background:#172338;position:sticky;top:0;"><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">#</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);text-align:left;">Siêu Thị</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);text-align:left;">Mã PT</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);text-align:left;">Barcode / Kiện</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">WMS</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">KDB</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">Lệch</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">Giá Vốn</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">Thành Tiền</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);">Kết Quả</th><th style="padding:8px;border:1px solid rgba(148,163,184,0.15);text-align:left;">Ghi Chú</th></tr></thead><tbody id="fmcg-m-tbody"></tbody></table></div></div>`;
        window.renderFmcgModalRows();
    };

    window.renderFmcgModalRows=function(){
        const items=window._fmcgModalItems||[];
        const q=(document.getElementById('fmcg-m-search')?.value||'').trim().toLowerCase();
        const st=document.getElementById('fmcg-m-status')?.value||'all';
        const filtered=items.filter(r=>{if(st!=='all'&&r.status!==st)return false;if(q&&!((r.st||'').toLowerCase().includes(q)||(r.store_name||'').toLowerCase().includes(q)||(r.pt||'').toLowerCase().includes(q)||(r.sku||'').toLowerCase().includes(q)||(r.sku_name||'').toLowerCase().includes(q)||(r.note||'').toLowerCase().includes(q)))return false;return true;});
        const totVal=filtered.reduce((a,r)=>a+(r.val||0),0);
        const sumEl=document.getElementById('fmcg-m-sum');
        if(sumEl)sumEl.innerHTML=`<strong>${filtered.length}</strong> dòng • Tổng tiền: <strong style="color:#38bdf8;">${progFmtVND(totVal)}</strong>`;
        const tbody=document.getElementById('fmcg-m-tbody');
        if(!tbody)return;
        tbody.innerHTML=filtered.map((r,i)=>`<tr style="border-bottom:1px solid rgba(148,163,184,0.1);"><td style="padding:7px 8px;text-align:center;color:#94a3b8;">${i+1}</td><td style="padding:7px 8px;"><strong>${r.st}</strong>${r.store_name?' - '+r.store_name:''}</td><td style="padding:7px 8px;color:#38bdf8;"><code>${r.pt||'-'}</code></td><td style="padding:7px 8px;"><div><strong>${r.sku}</strong></div>${r.sku_name?`<div style="color:#94a3b8;font-size:0.73rem;">${r.sku_name}</div>`:''}</td><td style="padding:7px 8px;text-align:right;">${progFmtN(r.wms)}</td><td style="padding:7px 8px;text-align:right;">${progFmtN(r.kdb)}</td><td style="padding:7px 8px;text-align:right;color:#f87171;"><strong>${progFmtN(r.lech)}</strong></td><td style="padding:7px 8px;text-align:right;">${progFmtVND(r.cost)}</td><td style="padding:7px 8px;text-align:right;color:#38bdf8;"><strong>${progFmtVND(r.val)}</strong></td><td style="padding:7px 8px;text-align:center;">${r.status==='Chưa XL'?`<span style="background:rgba(251,146,60,0.18);color:#fb923c;border:1px solid rgba(251,146,60,0.4);padding:2px 8px;border-radius:999px;font-size:0.71rem;font-weight:700;">🟡 ${r.dest}</span>`:`<span style="background:rgba(16,185,129,0.18);color:#34d399;border:1px solid rgba(16,185,129,0.4);padding:2px 8px;border-radius:999px;font-size:0.71rem;font-weight:700;">🟢 ${r.dest}</span>`}</td><td style="padding:7px 8px;color:#cbd5e1;font-size:0.75rem;">${r.note||'-'}</td></tr>`).join('')||`<tr><td colspan="11" style="padding:2rem;text-align:center;color:#94a3b8;">Không có dòng chi tiết phù hợp</td></tr>`;
    };

    // =========================================================================
    // ĐỒNG BỘ REALTIME (CDC StarRocks + Google Sheet Seedlog)
    // =========================================================================
    window.syncFmcgRealtime = async function () {
        const btn = document.getElementById('btn-fmcg-realtime');
        const origHtml = '<i class="fa-solid fa-bolt-lightning"></i> Cập Nhật Realtime (CDC & Seedlog)';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kéo CDC StarRocks & Seedlog (~15s)...';
        }
        const resetBtn = () => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml;
            }
        };

        // 1. Tìm endpoint Runner (Cloudflare HTTPS Tunnel trước, sau đó Localhost)
        let candidateUrls = [];
        try {
            const r = await fetch('runner_remote_url.json?t=' + Date.now());
            if (r.ok) {
                const j = await r.json();
                if (j && j.tunnel_url && j.status === 'online') {
                    candidateUrls.push(j.tunnel_url);
                }
            }
        } catch (e) { }
        candidateUrls.push('http://127.0.0.1:8088');
        candidateUrls.push('http://localhost:8088');

        for (const url of candidateUrls) {
            try {
                const ctrl = new AbortController();
                const tid = setTimeout(() => ctrl.abort(), 90000); // 90s cho CDC + Seedlog
                const res = await fetch(`${url}/api/sync_fmcg?push=true`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ push: true }),
                    signal: ctrl.signal
                });
                clearTimeout(tid);
                if (res.ok) {
                    const payload = await res.json();
                    if (payload.success && payload.data) {
                        window.FMCG_MATRIX_DATA = payload.data;
                        currentData = JSON.parse(JSON.stringify(payload.data));
                        buildUI();
                        resetBtn();
                        alert(
                            `🎉 ĐỒNG BỘ REALTIME THÀNH CÔNG (CDC STARROCKS + GOOGLE SHEET SEEDLOG)!\n\n` +
                            `• Giờ cập nhật mới: ${currentData.updated_at || 'Vừa xong'}\n` +
                            `• Phạm vi: ${currentData.dates ? currentData.dates.length : 0} ngày (đến ${currentData.summary?.latest_cdc_date || ''})\n` +
                            `• Đã hiển thị số mới ngay trên Web và tự động đẩy lên GitHub!`
                        );
                        return;
                    }
                }
            } catch (err) {
                console.warn('Thử runner FMCG không thành công:', url, err);
            }
        }

        resetBtn();
        alert(
            '⚠️ KHÔNG KẾT NỐI ĐƯỢC TRẠM RUNNER CỤC BỘ!\n\n' +
            '• Database CDC StarRocks (103.140.248.250) yêu cầu máy trạm đang bật NetBird + chạy Local Runner.\n' +
            '• Hãy chạy file "Chay_Local_Runner.bat" (hoặc "Chay_An_Local_Runner.vbs") trên máy tính, sau đó bấm lại nút Cập Nhật Realtime trên Web!'
        );
    };

    window.fetchGoogleSheetFmcgLive = window.syncFmcgRealtime;
})();
