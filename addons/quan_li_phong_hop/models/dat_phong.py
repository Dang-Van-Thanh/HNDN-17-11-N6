from odoo import models, fields, api, exceptions
from datetime import datetime
import requests

class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đăng ký mượn phòng"

    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True)
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True)  
    thoi_gian_muon_du_kien = fields.Datetime(string="Thời gian mượn dự kiến", required=True)
    thoi_gian_muon_thuc_te = fields.Datetime(string="Thời gian mượn thực tế")
    thoi_gian_tra_du_kien = fields.Datetime(string="Thời gian trả dự kiến", required=True)
    thoi_gian_tra_thuc_te = fields.Datetime(string="Thời gian trả thực tế")

    trang_thai = fields.Selection([
        ("chờ_duyệt", "Chờ duyệt"),
        ("đã_duyệt", "Đã duyệt"),
        ("đang_sử_dụng", "Đang sử dụng"),
        ("đã_hủy", "Đã hủy"),
        ("đã_trả", "Đã trả")
    ], string="Trạng thái", default="chờ_duyệt")

    lich_su_ids = fields.One2many("lich_su_thay_doi", "dat_phong_id", string="Lịch sử mượn trả")
    chi_tiet_su_dung_ids = fields.One2many("dat_phong", "phong_id", string="Chi Tiết Sử Dụng", domain=[("trang_thai", "in", ["đang_sử_dụng", "đã_trả"])])
    def xac_nhan_duyet_phong(self):
        """ Xác nhận duyệt phòng và tự động hủy các yêu cầu bị trùng thời gian (cùng phòng hoặc khác phòng) """
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể duyệt yêu cầu có trạng thái 'Chờ duyệt'.")
            
            # Duyệt yêu cầu hiện tại
            record.write({"trang_thai": "đã_duyệt"})
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

            # Hủy các yêu cầu cùng phòng có thời gian trùng lặp
            cung_phong_trung_thoi_gian = [
                ('phong_id', '=', record.phong_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_cung_phong_trung_thoi_gian = self.search(cung_phong_trung_thoi_gian)
            for other in xu_li_cung_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.env["lich_su_thay_doi"].create({
                    "dat_phong_id": other.id,
                    "nguoi_muon_id": other.nguoi_muon_id.id,
                    "thoi_gian_muon_du_kien": other.thoi_gian_muon_du_kien,
                    "thoi_gian_muon_thuc_te": other.thoi_gian_muon_thuc_te,
                    "thoi_gian_tra_du_kien": other.thoi_gian_tra_du_kien,
                    "thoi_gian_tra_thuc_te": other.thoi_gian_tra_thuc_te,
                    "trang_thai": other.trang_thai
                })

            # Hủy các yêu cầu khác phòng nhưng của cùng một người mượn nếu bị trùng thời gian
            khac_phong_trung_thoi_gian = [
                ('nguoi_muon_id', '=', record.nguoi_muon_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_khac_phong_trung_thoi_gian = self.search(khac_phong_trung_thoi_gian)
            for other in xu_li_khac_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.env["lich_su_thay_doi"].create({
                    "dat_phong_id": other.id,
                    "nguoi_muon_id": other.nguoi_muon_id.id,
                    "thoi_gian_muon_du_kien": other.thoi_gian_muon_du_kien,
                    "thoi_gian_muon_thuc_te": other.thoi_gian_muon_thuc_te,
                    "thoi_gian_tra_du_kien": other.thoi_gian_tra_du_kien,
                    "thoi_gian_tra_thuc_te": other.thoi_gian_tra_thuc_te,
                    "trang_thai": other.trang_thai
                })

    def huy_muon_phong(self):
        """ Hủy đăng ký mượn phòng """
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Chờ duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

    def huy_da_duyet(self):
        """ Hủy yêu cầu đã duyệt """
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Đã duyệt'.")
            
            record.write({"trang_thai": "đã_hủy"})
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

    def bat_dau_su_dung(self):
        """ Bắt đầu sử dụng phòng - Cập nhật thời gian mượn thực tế """
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể bắt đầu sử dụng phòng có trạng thái 'Đã duyệt'.")

            # Kiểm tra nếu đã có người đang sử dụng phòng này
            kiem_tra_phong = self.env["dat_phong"].search([
                ("phong_id", "=", record.phong_id.id),
                ("trang_thai", "=", "đang_sử_dụng"),
                ("id", "!=", record.id)
            ])

            if kiem_tra_phong:
                raise exceptions.UserError(f"Phòng {record.phong_id.name} hiện đang được sử dụng. Vui lòng chờ đến khi phòng trống.")

            # Nếu không có ai đang sử dụng, cho phép bắt đầu
            record.write({
                "trang_thai": "đang_sử_dụng",
                "thoi_gian_muon_thuc_te": datetime.now()
            })

            # Cập nhật trạng thái tài sản trong phòng: chuyển sang "Muon"
            if record.phong_id.tai_san_ids:
                record.phong_id.tai_san_ids.write({"trang_thai": "Muon"})
                # Tạo lịch sử sử dụng cho từng tài sản
                for tai_san in record.phong_id.tai_san_ids:
                    self.env["lich_su_su_dung"].create({
                        "ngay_muon": record.thoi_gian_muon_thuc_te,
                        "nhan_vien_id": record.nguoi_muon_id.id,
                        "tai_san_id": tai_san.id,
                        "ghi_chu": f"Sử dụng trong phòng {record.phong_id.name}",
                        "dat_phong_id": record.id
                    })

            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })


    def tra_phong(self):
        """ Trả phòng - Cập nhật thời gian trả thực tế và đảm bảo thời gian mượn thực tế có giá trị """
        for record in self:
            if record.trang_thai != "đang_sử_dụng":
                raise exceptions.UserError("Chỉ có thể trả phòng đang ở trạng thái 'Đang sử dụng'.")
            current_time = datetime.now()
            record.write({
                "trang_thai": "đã_trả",
                "thoi_gian_tra_thuc_te": current_time,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te or current_time
            })

            # Cập nhật trạng thái tài sản trong phòng: chuyển về "CatGiu"
            if record.phong_id.tai_san_ids:
                record.phong_id.tai_san_ids.write({"trang_thai": "CatGiu"})
                # Cập nhật lịch sử sử dụng: đặt ngày trả
                lich_su_records = self.env["lich_su_su_dung"].search([
                    ("dat_phong_id", "=", record.id),
                    ("ngay_tra", "=", False)
                ])
                lich_su_records.write({"ngay_tra": record.thoi_gian_tra_thuc_te})

            # Lưu vào lịch sử sử dụng tài sản
            tai_san = record.phong_id.tai_san_id
            if tai_san:
                self.env["lich_su_su_dung"].create({
                    "ngay_muon": record.thoi_gian_muon_thuc_te,
                    "ngay_tra": record.thoi_gian_tra_thuc_te,
                    "nhan_vien_id": record.nguoi_muon_id.id,
                    "tai_san_id": tai_san.id,
                    "ghi_chu": f"Mượn phòng {record.phong_id.name}"
                })

            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

    @api.model
    def _get_available_rooms(self, thoi_gian_bd, thoi_gian_kt, suc_chua):
        """Trả về phòng họp trống để gợi ý theo yêu cầu"""
        if not (thoi_gian_bd and thoi_gian_kt and suc_chua):
            return self.env['quan_ly_phong_hop'].sudo().search([])

        # Loại bỏ phòng đang bị đặt trong khung thời gian tương ứng
        query = [
            ('trang_thai', 'in', ['chờ_duyệt', 'đã_duyệt', 'đang_sử_dụng']),
            ('thoi_gian_muon_du_kien', '<', thoi_gian_kt),
            ('thoi_gian_tra_du_kien', '>', thoi_gian_bd),
        ]
        booked_rooms = self.search(query).mapped('phong_id').ids

        candidates = self.env['quan_ly_phong_hop'].sudo().search([
            ('suc_chua', '>=', suc_chua),
            ('id', 'not in', booked_rooms)
        ])
        return candidates

    @api.model
    def _call_gemini_api(self, prompt):
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('quan_li_phong_hop.gemini_api_key')
        if not api_key:
            return 'Chưa cấu hình API Gemini. Sử dụng gợi ý nội bộ.'

        # Validate API key format
        if not api_key.startswith('AIzaSy') or len(api_key) < 35:
            return 'API key không hợp lệ. API key phải bắt đầu bằng "AIzaSy" và có độ dài ít nhất 35 ký tự.'

        # Sử dụng Gemini 2.5 Flash - model mới nhất có sẵn
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
            }],
            'generationConfig': {
                'temperature': 0.2,
                'maxOutputTokens': 400,
            }
        }

        try:
            result = requests.post(url, json=payload, headers=headers, timeout=30)
            result.raise_for_status()
            data = result.json()

            # Parse response từ Gemini API
            if 'candidates' in data and data['candidates']:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    return candidate['content']['parts'][0].get('text', '').strip()

            return 'Gemini trả về kết quả rỗng.'
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f'Không tìm thấy endpoint API. Vui lòng kiểm tra API key và quyền truy cập.'
            elif e.response.status_code == 403:
                return f'API key không có quyền truy cập. Vui lòng kiểm tra API key.'
            elif e.response.status_code == 429:
                return f'Quá nhiều yêu cầu. Vui lòng thử lại sau.'
            else:
                return f'Lỗi HTTP {e.response.status_code}: {e.response.text}'
        except requests.exceptions.Timeout:
            return 'Timeout khi kết nối đến Gemini API.'
        except requests.exceptions.ConnectionError:
            return 'Không thể kết nối đến Gemini API. Kiểm tra kết nối internet.'
        except Exception as e:
            return f'Không thể kết nối Gemini: {str(e)}'

    @api.model
    def suggest_room_for_time_capacity(self, thoi_gian_bd, thoi_gian_kt, suc_chua):
        rooms = self._get_available_rooms(thoi_gian_bd, thoi_gian_kt, suc_chua)
        if not rooms:
            return {
                'choices': rooms,
                'ai_report': 'Không có phòng phù hợp trong khoảng thời gian và sức chứa này.'
            }

        top3 = rooms.sorted(key=lambda r: r.suc_chua)[:3]
        room_list = '\n'.join([f"- {r.name} (sức chứa {r.suc_chua})" for r in top3])

        prompt = (
            f"Bạn là trợ lý đặt phòng họp. Dựa vào yêu cầu:\n"
            f"* Thời gian từ {thoi_gian_bd} đến {thoi_gian_kt}\n"
            f"* Sức chứa ít nhất {suc_chua} người\n"
            f"Danh sách phòng hiện khả dụng:\n{room_list}\n"
            "Hãy đề xuất phòng tốt nhất kèm lý do ngắn gọn."
        )

        ai_response = self._call_gemini_api(prompt)
        return {
            'choices': rooms,
            'ai_report': ai_response,
        }

    def open_gemini_suggestion_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gợi ý AI Gemini',
            'res_model': 'dat_phong.gemini.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_thoi_gian_muon_du_kien': self.thoi_gian_muon_du_kien,
                'default_thoi_gian_tra_du_kien': self.thoi_gian_tra_du_kien,
            },
        }

    @api.constrains('phong_id', 'thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien')
    def _check_trung_gio_phong(self):
        for record in self:
            if record.phong_id and record.thoi_gian_muon_du_kien and record.thoi_gian_tra_du_kien:
                trung_lap = self.search([
                    ('phong_id', '=', record.phong_id.id),
                    ('id', '!=', record.id),
                    ('trang_thai', 'in', ['chờ_duyệt', 'đã_duyệt', 'đang_sử_dụng']),
                    ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                    ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
                ])
                if trung_lap:
                    raise exceptions.ValidationError(f"Phòng {record.phong_id.name} đã có yêu cầu đặt vào thời gian này. Vui lòng chọn thời gian khác.")
