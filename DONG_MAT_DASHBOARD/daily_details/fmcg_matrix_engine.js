/**
 * FMCG MATRIX ENGINE - Tab 8: Báo Cáo Logistics Kho Khô FMCG (Seedlog)
 * Tự động kết xuất Bảng ma trận 48 dòng chỉ số từ 01/11/2026 trở đi
 */

(function () {
    let currentData = null;
    let sortDescending = true; // true = Mới nhất trước (17/11 -> 01/11), false = 01/11 -> 17/11
    let filterSection = 'all';
    let searchQuery = '';

    // Khởi tạo hoặc render khi chuyển sang Tab 8
    window.renderFmcgMatrix = function () {
        if (!currentData) {
            if (window.FMCG_MATRIX_DATA) {
                currentData = JSON.parse(JSON.stringify(window.FMCG_MATRIX_DATA));
            } else {
                fetchGoogleSheetFmcgLive(true);
                return;
            }
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
        renderMatrixTable();
    }

    function renderKPICards() {
        const s = currentData.summary || {};
        const kpiContainer = document.getElementById('fmcg-kpi-cards');
        if (!kpiContainer) return;

        kpiContainer.innerHTML = `
            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(6,182,212,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(6,182,212,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(6,182,212,0.18); color:#06b6d4; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-chart-line"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">Tổng Chuyển Lũy Kế</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#38bdf8; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.tong_luy_ke || '0'} <span style="font-size:0.78rem; font-weight:600; color:#cbd5e1;">VNĐ</span></div>
                    <div style="font-size:0.72rem; color:#64748b;">Lũy kế toàn kỳ (đến ${s.latest_date || ''})</div>
                </div>
            </div>

            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(245,158,11,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(245,158,11,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(245,158,11,0.18); color:#f59e0b; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-scale-unbalanced"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">Tồn Kho Chênh Lệch</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#fbbf24; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.ton_kho_chenh_lech || '0'} <span style="font-size:0.78rem; font-weight:600; color:#cbd5e1;">VNĐ</span></div>
                    <div style="font-size:0.72rem; color:#64748b;">Giá trị đang treo xử lý</div>
                </div>
            </div>

            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(236,72,153,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(236,72,153,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(236,72,153,0.18); color:#ec4899; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-percent"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">Tỷ Lệ Lệch Chuyển Hàng</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#f43f5e; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.ty_le_chenh_lech || '0.00%'}</div>
                    <div style="font-size:0.72rem; color:#64748b;">Ngưỡng an toàn &lt; 0.30%</div>
                </div>
            </div>

            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(16,185,129,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(16,185,129,0.18); color:#10b981; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-truck-fast"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">SL Chuyển (Ngày ${s.latest_date ? s.latest_date.slice(0,5) : ''})</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#34d399; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.sl_chuyen_ngay || '0'} <span style="font-size:0.78rem; font-weight:600; color:#cbd5e1;">món</span></div>
                    <div style="font-size:0.72rem; color:#64748b;">Giá trị: ${s.gia_tri_chuyen_ngay || '0'} đ</div>
                </div>
            </div>

            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(139,92,246,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(139,92,246,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(139,92,246,0.18); color:#8b5cf6; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">Lệch Ngày ${s.latest_date ? s.latest_date.slice(0,5) : ''}</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#a78bfa; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.sl_chenh_lech_ngay || '0'} <span style="font-size:0.78rem; font-weight:600; color:#cbd5e1;">món</span></div>
                    <div style="font-size:0.72rem; color:#64748b;">Tiền lệch: ${s.gia_tri_chenh_lech_ngay || '0'} đ</div>
                </div>
            </div>

            <div class="kpi-fmcg-card" style="background:linear-gradient(135deg, rgba(56,189,248,0.12), rgba(15,23,42,0.6)); border:1px solid rgba(56,189,248,0.3); border-radius:12px; padding:1.1rem; display:flex; align-items:center; gap:0.9rem;">
                <div style="width:48px; height:48px; border-radius:10px; background:rgba(56,189,248,0.18); color:#38bdf8; display:flex; align-items:center; justify-content:center; font-size:1.4rem;">
                    <i class="fa-solid fa-store"></i>
                </div>
                <div>
                    <div style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8; font-weight:700; letter-spacing:0.5px;">Siêu Thị Có Lệch</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#38bdf8; font-family:'JetBrains Mono', monospace; margin:0.15rem 0;">${s.sl_st_chenh_lech || '0'} <span style="font-size:0.78rem; font-weight:600; color:#cbd5e1;">cửa hàng</span></div>
                    <div style="font-size:0.72rem; color:#64748b;">DC xác nhận: ${s.gia_tri_tra_dc || '0'} đ</div>
                </div>
            </div>
        `;
    }

    function renderMatrixTable() {
        const container = document.getElementById('fmcg-table-container');
        if (!container) return;

        // Xử lý danh sách ngày theo chiều sắp xếp (sortDescending)
        let dates = [...currentData.dates];
        if (sortDescending) {
            dates.reverse(); // Ngày mới nhất ở cột đầu tiên
        }

        // Lọc danh sách sections và metrics
        const sections = currentData.sections || [];
        const q = searchQuery.trim().toLowerCase();

        let tableHtml = `
            <table class="fmcg-matrix-table" style="width:100%; border-collapse:collapse; font-size:0.84rem; text-align:right;">
                <thead>
                    <tr style="background:#0f172a; position:sticky; top:0; z-index:20; border-bottom:2px solid rgba(56,189,248,0.3);">
                        <th style="position:sticky; left:0; z-index:25; background:#0f172a; min-width:270px; max-width:320px; text-align:left; padding:0.85rem 1rem; color:#38bdf8; font-weight:800; border-right:2px solid rgba(255,255,255,0.1); box-shadow: 2px 0 6px rgba(0,0,0,0.5);">
                            <div style="display:flex; align-items:center; justify-content:space-between;">
                                <span>CHỈ SỐ BÁO CÁO LOGISTICS</span>
                                <span style="font-size:0.7rem; font-weight:600; color:#64748b; background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px;">${dates.length} NGÀY</span>
                            </div>
                        </th>
        `;

        dates.forEach(d => {
            const isToday = isDateCurrent(d.iso);
            tableHtml += `
                <th style="min-width:115px; padding:0.75rem 0.65rem; text-align:right; color:${isToday ? '#38bdf8' : '#e2e8f0'}; font-weight:700; border-right:1px solid rgba(255,255,255,0.06); background:${isToday ? 'rgba(56,189,248,0.1)' : '#0f172a'};">
                    <div style="font-size:0.85rem; font-family:'JetBrains Mono', monospace;">${d.display}</div>
                    <div style="font-size:0.7rem; color:#64748b; font-weight:500;">${getDayOfWeek(d.iso)}</div>
                </th>
            `;
        });

        tableHtml += `</tr></thead><tbody>`;

        let visibleRowsCount = 0;

        sections.forEach(sec => {
            if (filterSection !== 'all' && sec.id !== filterSection) {
                return;
            }

            // Lọc các hàng trong section theo ô tìm kiếm
            const filteredRows = sec.rows.filter(r => {
                if (!q) return true;
                return r.name.toLowerCase().includes(q);
            });

            if (filteredRows.length === 0) return;

            visibleRowsCount += filteredRows.length;

            // Dòng Tiêu đề Section (Header Row)
            tableHtml += `
                <tr style="background:linear-gradient(90deg, ${sec.accent}22, rgba(15,23,42,0.9)); border-top:1px solid rgba(255,255,255,0.12); border-bottom:1px solid rgba(255,255,255,0.08);">
                    <td colspan="${dates.length + 1}" style="position:sticky; left:0; z-index:15; padding:0.65rem 1rem; text-align:left; font-weight:800; color:${sec.accent}; font-size:0.85rem; letter-spacing:0.5px;">
                        <i class="${sec.icon}" style="margin-right:0.6rem;"></i> ${sec.title}
                    </td>
                </tr>
            `;

            // Từng dòng chỉ số (Metric Rows)
            filteredRows.forEach((rowItem, rIdx) => {
                const isEven = rIdx % 2 === 0;
                tableHtml += `
                    <tr class="fmcg-data-row" style="background:${isEven ? '#161b22' : '#11161d'}; border-bottom:1px solid rgba(255,255,255,0.04); transition:background 0.15s ease;">
                        <td style="position:sticky; left:0; z-index:12; background:${isEven ? '#161b22' : '#11161d'}; text-align:left; padding:0.65rem 1rem; font-weight:600; color:#cbd5e1; border-right:2px solid rgba(255,255,255,0.08); box-shadow: 2px 0 5px rgba(0,0,0,0.3); white-space:nowrap;">
                            ${formatMetricTitle(rowItem.name)}
                        </td>
                `;

                dates.forEach(d => {
                    const val = rowItem.values[d.iso] || '';
                    const cellFormatted = formatCellValue(val, rowItem.name);
                    tableHtml += `
                        <td style="padding:0.65rem 0.65rem; border-right:1px solid rgba(255,255,255,0.04); font-family:'JetBrains Mono', monospace; font-size:0.81rem; white-space:nowrap;">
                            ${cellFormatted}
                        </td>
                    `;
                });

                tableHtml += `</tr>`;
            });
        });

        if (visibleRowsCount === 0) {
            tableHtml += `
                <tr>
                    <td colspan="${dates.length + 1}" style="padding:2.5rem; text-align:center; color:#64748b;">
                        <i class="fa-solid fa-magnifying-glass" style="font-size:1.5rem; margin-bottom:0.5rem; display:block;"></i>
                        Không tìm thấy chỉ số nào khớp với từ khóa "<strong>${searchQuery}</strong>"
                    </td>
                </tr>
            `;
        }

        tableHtml += `</tbody></table>`;
        container.innerHTML = tableHtml;

        // Cập nhật nhãn trạng thái tổng
        const statusLabel = document.getElementById('fmcg-status-text');
        if (statusLabel) {
            statusLabel.innerHTML = `Đang hiển thị <strong>${visibleRowsCount}</strong> chỉ số • <strong>${dates.length}</strong> ngày (từ 01/11/2026)`;
        }
    }

    function formatMetricTitle(name) {
        if (name.includes('chênh lệch') || name.includes('trễ timeline')) {
            return `<span style="color:#fb7185;">${name}</span>`;
        }
        if (name.includes('trả DC') || name.includes('xác nhận')) {
            return `<span style="color:#38bdf8;">${name}</span>`;
        }
        if (name.includes('lũy kế') || name.includes('Tồn kho')) {
            return `<strong style="color:#34d399;">${name}</strong>`;
        }
        return name;
    }

    function formatCellValue(val, metricName) {
        if (!val || val === '#DIV/0!' || val === '#N/A' || val === '-') {
            return `<span style="color:#475569;">-</span>`;
        }

        const isPercent = val.includes('%');
        const isNegative = val.startsWith('-');

        if (isPercent) {
            if (val === '0.00%' || val === '0%') {
                return `<span style="color:#64748b;">0.00%</span>`;
            }
            if (isNegative) {
                return `<span style="color:#f87171; font-weight:700;">${val}</span>`;
            }
            return `<span style="color:#38bdf8; font-weight:600;">${val}</span>`;
        }

        if (isNegative) {
            return `<span style="color:#f87171; font-weight:700; background:rgba(244,63,94,0.12); padding:1px 5px; border-radius:4px;">${val}</span>`;
        }

        if (val === '0') {
            return `<span style="color:#475569;">0</span>`;
        }

        // Điểm nhấn cho dòng lũy kế hoặc giá trị
        if (metricName.includes('Tổng giá trị') || metricName.includes('Tồn kho')) {
            return `<strong style="color:#34d399;">${val}</strong>`;
        }

        return `<span style="color:#f1f5f9;">${val}</span>`;
    }

    function getDayOfWeek(isoDate) {
        try {
            const d = new Date(isoDate);
            const days = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
            return days[d.getDay()] || '';
        } catch (e) {
            return '';
        }
    }

    function isDateCurrent(isoDate) {
        const today = new Date().toISOString().slice(0, 10);
        return isoDate === today;
    }

    // Các hàm tương tác người dùng
    window.toggleFmcgSort = function () {
        sortDescending = !sortDescending;
        const btn = document.getElementById('btn-fmcg-sort');
        if (btn) {
            btn.innerHTML = sortDescending 
                ? `<i class="fa-solid fa-arrow-down-wide-short"></i> Ngày Mới Nhất Trước`
                : `<i class="fa-solid fa-arrow-up-wide-short"></i> Ngày Cũ Nhất Trước`;
        }
        renderMatrixTable();
    };

    window.filterFmcgSection = function (secId) {
        filterSection = secId;
        const buttons = document.querySelectorAll('.fmcg-sec-pill');
        buttons.forEach(b => {
            if (b.getAttribute('data-sec') === secId) {
                b.style.background = '#0284c7';
                b.style.borderColor = '#38bdf8';
                b.style.color = '#fff';
            } else {
                b.style.background = '#1e293b';
                b.style.borderColor = 'rgba(255,255,255,0.08)';
                b.style.color = '#94a3b8';
            }
        });
        renderMatrixTable();
    };

    window.searchFmcgMetrics = function (input) {
        searchQuery = input.value || '';
        renderMatrixTable();
    };

    window.exportFmcgExcel = function () {
        if (!currentData || !currentData.dates || !window.XLSX) {
            alert('Chưa có dữ liệu hoặc thư viện Excel chưa tải xong.');
            return;
        }

        try {
            const wb = XLSX.utils.book_new();
            const wsData = [];

            // Header
            const headerRow = ['Tên Chỉ Số'];
            let dates = [...currentData.dates];
            if (sortDescending) dates.reverse();

            dates.forEach(d => headerRow.push(d.display));
            wsData.push(headerRow);

            // Rows
            currentData.sections.forEach(sec => {
                wsData.push([`--- ${sec.title} ---`, ...dates.map(() => '')]);
                sec.rows.forEach(r => {
                    const row = [r.name];
                    dates.forEach(d => {
                        row.push(r.values[d.iso] || '');
                    });
                    wsData.push(row);
                });
            });

            const ws = XLSX.utils.aoa_to_sheet(wsData);
            XLSX.utils.book_append_sheet(wb, ws, "FMCG_Logistics_Matrix");
            const filename = `Bao_Cao_FMCG_Logistics_T11_2026_${new Date().toISOString().slice(0,10)}.xlsx`;
            XLSX.writeFile(wb, filename);
        } catch (err) {
            console.error('Lỗi xuất Excel:', err);
            alert('Lỗi xuất file Excel: ' + err.message);
        }
    };

    // Tải lại trực tiếp từ Google Sheet
    window.fetchGoogleSheetFmcgLive = function (silent = false) {
        const btn = document.getElementById('btn-fmcg-refresh');
        if (btn) {
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang tải Google Sheet...`;
            btn.disabled = true;
        }

        const url = 'https://docs.google.com/spreadsheets/d/1ZTLRCJjr-8surASFt9Rm6M-2SYJZfa2dc2phS6vg4_k/export?format=csv&gid=1213759414&t=' + Date.now();

        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.text();
            })
            .then(csvText => {
                parseAndSetCsvData(csvText);
                if (!silent) {
                    alert('Đã cập nhật dữ liệu mới nhất từ Google Sheet FMCG thành công!');
                }
            })
            .catch(err => {
                console.warn('Không thể fetch trực tiếp Google Sheet (có thể do CORS), sử dụng cache:', err);
                if (window.FMCG_MATRIX_DATA) {
                    currentData = JSON.parse(JSON.stringify(window.FMCG_MATRIX_DATA));
                    buildUI();
                    if (!silent) alert('Đã nạp lại dữ liệu từ cache hệ thống.');
                } else if (!silent) {
                    alert('Không thể kết nối đến Google Sheet: ' + err.message);
                }
            })
            .finally(() => {
                if (btn) {
                    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Cập Nhật Google Sheet`;
                    btn.disabled = false;
                }
            });
    };

    function parseAndSetCsvData(csvText) {
        // Parse CSV lines
        const lines = [];
        let row = [];
        let inQuotes = false;
        let cur = '';

        for (let i = 0; i < csvText.length; i++) {
            const ch = csvText[i];
            const nextCh = csvText[i + 1];

            if (ch === '"') {
                if (inQuotes && nextCh === '"') {
                    cur += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (ch === ',' && !inQuotes) {
                row.push(cur);
                cur = '';
            } else if ((ch === '\r' || ch === '\n') && !inQuotes) {
                if (ch === '\r' && nextCh === '\n') i++;
                row.push(cur);
                cur = '';
                lines.push(row);
                row = [];
            } else {
                cur += ch;
            }
        }
        if (cur || row.length > 0) {
            row.push(cur);
            lines.push(row);
        }

        if (lines.length < 4) return;
        const header = lines[2];

        // Lọc ngày tháng 11/2026 trở đi (col >= 62)
        const dateCols = [];
        for (let idx = 1; idx < header.length; idx++) {
            const colStr = (header[idx] || '').trim();
            if (!colStr) continue;
            
            // Format check
            const parts = colStr.replace(/-/g, '/').split('/');
            if (parts.length === 3) {
                const p1 = parseInt(parts[0], 10);
                const p2 = parseInt(parts[1], 10);
                const p3 = parseInt(parts[2], 10);
                const year = p3 >= 2000 ? p3 : 2000 + p3;

                // Col 1..61 are Oct and Sept. Col 62+ are Nov+
                if (idx >= 62 && (p1 === 11 || p2 === 11 || p1 > 11 || p2 > 11 || year > 2026)) {
                    const month = p1 === 11 ? p1 : (p2 === 11 ? p2 : p1);
                    const day = p1 === 11 ? p2 : (p2 === 11 ? p1 : p2);
                    const mm = String(month).padStart(2, '0');
                    const dd = String(day).padStart(2, '0');
                    const iso = `${year}-${mm}-${dd}`;
                    const display = `${dd}/${mm}/${year}`;
                    dateCols.push({ col_idx: idx, raw_date: colStr, iso_date: iso, display_date: display });
                }
            }
        }

        dateCols.sort((a, b) => a.iso_date.localeCompare(b.iso_date));

        // Tái tạo sections & metrics
        const sectionsDef = [
            { id: "sec_san_luong", title: "1. SẢN LƯỢNG HÀNG HÓA (SL)", icon: "fa-solid fa-boxes-stacked", accent: "#38bdf8", rStart: 3, rEnd: 10 },
            { id: "sec_gia_tri", title: "2. GIÁ TRỊ HÀNG HÓA (VNĐ)", icon: "fa-solid fa-coins", accent: "#f59e0b", rStart: 10, rEnd: 17 },
            { id: "sec_ty_le", title: "3. TỶ LỆ CHÊNH LỆCH & HOÀN TẤT (%)", icon: "fa-solid fa-percent", accent: "#ec4899", rStart: 17, rEnd: 23 },
            { id: "sec_sieu_thi", title: "4. SỐ LƯỢNG SIÊU THỊ / CỬA HÀNG", icon: "fa-solid fa-shop", accent: "#10b981", rStart: 23, rEnd: 30 },
            { id: "sec_dc_phan_hoi", title: "5. DC XÁC NHẬN & PHẢN HỒI", icon: "fa-solid fa-truck-ramp-box", accent: "#8b5cf6", rStart: 30, rEnd: 42 },
            { id: "sec_luy_ke", title: "6. LŨY KẾ TOÀN KỲ & TỒN KHO", icon: "fa-solid fa-chart-line", accent: "#06b6d4", rStart: 42, rEnd: 45 }
        ];

        const sections = [];
        const allMetrics = [];

        sectionsDef.forEach(sDef => {
            const secRows = [];
            for (let rI = sDef.rStart; rI < Math.min(sDef.rEnd, lines.length); rI++) {
                const r = lines[rI];
                const mName = (r[0] || '').trim();
                if (!mName) continue;

                const values = {};
                dateCols.forEach(dc => {
                    values[dc.iso_date] = (r[dc.col_idx] || '').trim();
                });

                const rObj = { row_idx: rI + 1, name: mName, section_id: sDef.id, values };
                secRows.push(rObj);
                allMetrics.push(rObj);
            }
            sections.push({ id: sDef.id, title: sDef.title, icon: sDef.icon, accent: sDef.accent, rows: secRows });
        });

        const latestDc = dateCols[dateCols.length - 1];
        const latestIso = latestDc ? latestDc.iso_date : '';
        const getV = (name) => {
            const m = allMetrics.find(x => x.name.toLowerCase() === name.toLowerCase());
            return m ? (m.values[latestIso] || '') : '';
        };

        currentData = {
            updated_at: new Date().toLocaleString('vi-VN'),
            dates: dateCols.map(dc => ({ iso: dc.iso_date, display: dc.display_date, raw: dc.raw_date })),
            summary: {
                latest_date: latestDc ? latestDc.display_date : '',
                tong_luy_ke: getV("Tổng giá trị chuyển lũy kế"),
                ton_kho_chenh_lech: getV("Tồn kho chênh lệch"),
                ty_le_chenh_lech: getV("Tỷ lệ chênh lệch chuyển hàng"),
                sl_chuyen_ngay: getV("SL chuyển"),
                sl_chenh_lech_ngay: getV("SL chênh lệch"),
                gia_tri_chuyen_ngay: getV("Giá trị chuyển"),
                gia_tri_chenh_lech_ngay: getV("Giá trị chênh lệch"),
                sl_st_chenh_lech: getV("SL ST chênh lệch"),
                gia_tri_tra_dc: getV("Giá trị trả DC")
            },
            sections: sections
        };

        buildUI();
    }
})();
