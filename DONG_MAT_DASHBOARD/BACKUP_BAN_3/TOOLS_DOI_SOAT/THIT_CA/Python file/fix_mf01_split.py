import codecs
import re

def fix_app():
    with codecs.open('app_thit_ca.py', 'r', 'utf-8') as f:
        content = f.read()

    # Replace sql_mf01 query
    old_sql = r'sql_mf01 = f\"\"\"\s*SELECT\s*i\.to_branch_id,\s*i\.code as `Mã chuyển hàng`,\s*IFNULL\(c\.container_codes, i\.double_check_code\) as `Mã thùng`,\s*l\.barcode as `Mã hàng`,\s*l\.name as `Tên hàng`,\s*l\.unit__name as `ĐVT`,\s*CAST\(IFNULL\(l\.transfer_quantity, 0\) AS DOUBLE\) as `Số lượng chuyển`,\s*CAST\(IFNULL\(l\.store_quantity, 0\) AS DOUBLE\) as `Số lượng nhận`\s*FROM __cdc_kfm_kf_inventories_kf_transfer_items i\s*INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i\._id = l\._root_id\s*LEFT JOIN \(\s*SELECT _parent_id, GROUP_CONCAT\(code SEPARATOR \', \'\) as container_codes\s*FROM __cdc_kfm_kf_inventories_kf_transfer_items___container_lines\s*GROUP BY _parent_id\s*\) c ON i\._id = c\._parent_id\s*WHERE \{shortage_condition\}\s*AND DATE\(DATE_ADD\(i\.transfer_date, INTERVAL 7 HOUR\)\) = \'\{date_str\}\'\s*AND i\.status = 5\s*AND \(l\.barcode NOT LIKE \'CC%\' OR l\.barcode IS NULL\)\s*\"\"\"'
    
    new_sql = '''sql_mf01 = f"""
                    SELECT 
                        i.to_branch_id,
                        i.code as `Mã chuyển hàng`,
                        IFNULL(c.code, i.double_check_code) as `Mã thùng`,
                        l.barcode as `Mã hàng`,
                        l.name as `Tên hàng`,
                        l.unit__name as `ĐVT`,
                        CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                        CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
                    FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                    INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                    LEFT JOIN __cdc_kfm_kf_inventories_kf_transfer_items___container_lines c ON i._id = c._parent_id
                    WHERE {shortage_condition}
                      AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                      AND i.status = 5
                      AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                    """'''
    content = re.sub(old_sql, new_sql, content, count=0)

    with codecs.open('app_thit_ca.py', 'w', 'utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_app()
