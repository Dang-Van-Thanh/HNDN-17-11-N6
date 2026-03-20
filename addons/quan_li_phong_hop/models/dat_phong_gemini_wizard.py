from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta
import re

class DatPhongGeminiWizard(models.TransientModel):
    _name = 'dat_phong.gemini.wizard'
    _description = 'Gợi ý đặt phòng họp bằng AI Gemini'

    yeu_cau_text = fields.Text(
        string='Yêu cầu đặt phòng',
        required=True,
        default='Tôi cần phòng họp cho 10 người vào ngày 22/03/2026 bắt đầu 9:00, thời lượng 30 phút'
    )
    nguoi_muon_id = fields.Many2one('nhan_vien', string='Người mượn', required=True)
    goi_y_ai = fields.Text(string='Gợi ý AI Gemini', readonly=True)
    phong_id = fields.Many2one('quan_ly_phong_hop', string='Phòng đề xuất', readonly=True)

    def _parse_text_request(self, text):
        """Parse yêu cầu tự nhiên sang số người, ngày, giờ bắt đầu, và thời lượng (phút)"""
        result = {
            'suc_chua': None,
            'date': None,
            'start_time': None,
            'duration': None,
        }

        # Số người
        match_people = re.search(r'(\d+)\s*người', text, re.IGNORECASE)
        if match_people:
            result['suc_chua'] = int(match_people.group(1))

        # Duration
        match_duration = re.search(r'(?:thời gian|thời lượng)\s*(\d+)\s*phút', text, re.IGNORECASE)
        if match_duration:
            result['duration'] = int(match_duration.group(1))

        # Date dạng dd/mm hoặc dd/mm/yyyy
        match_date = re.search(r'((\d{1,2})/(\d{1,2})(?:/(\d{4}))?)', text)
        if match_date:
            d = int(match_date.group(2))
            m = int(match_date.group(3))
            y = int(match_date.group(4)) if match_date.group(4) else datetime.now().year
            try:
                result['date'] = datetime(year=y, month=m, day=d)
            except Exception:
                result['date'] = None

        # Thời gian bắt đầu dạng 9:00, 9h, 9 giờ
        match_start = re.search(r'bắt đầu\s*(\d{1,2})(?::(\d{1,2})|h(?:\s*(\d{1,2}))?)?\s*(?:giờ)?', text, re.IGNORECASE)
        if match_start:
            hour = int(match_start.group(1))
            minute = 0
            if match_start.group(2):
                minute = int(match_start.group(2))
            elif match_start.group(3):
                minute = int(match_start.group(3))
            result['start_time'] = (hour, minute)

        return result

    def action_get_ai_suggestion(self):
        """Gọi AI Gemini để phân tích yêu cầu và gợi ý phòng"""
        if not self.yeu_cau_text:
            self.write({'goi_y_ai': 'Vui lòng nhập yêu cầu đặt phòng.'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        parse = self._parse_text_request(self.yeu_cau_text)
        if not (parse['suc_chua'] and parse['date'] and parse['start_time'] and parse['duration']):
            self.write({'goi_y_ai': 'Không thể phân tích đầy đủ từ yêu cầu. Vui lòng ghi rõ: số người, ngày, giờ bắt đầu, thời lượng (phút).'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        start = datetime(year=parse['date'].year, month=parse['date'].month, day=parse['date'].day,
                         hour=parse['start_time'][0], minute=parse['start_time'][1])
        end = start + timedelta(minutes=parse['duration'])

        rooms = self.env['dat_phong'].sudo()._get_available_rooms(start, end, parse['suc_chua'])
        if not rooms:
            self.write({'goi_y_ai': 'Không có phòng trống phù hợp theo yêu cầu.'})
            return {'type': 'ir.actions.act_window', 'res_model': self._name, 'view_mode': 'form', 'res_id': self.id, 'target': 'new'}

        candidate_name = rooms.sorted(key=lambda r: r.suc_chua)[0].name
        candidate_id = rooms.sorted(key=lambda r: r.suc_chua)[0].id

        prompt = f"""
        Yêu cầu: {self.yeu_cau_text}
        Có {len(rooms)} phòng trống phù hợp với sức chứa tối thiểu {parse['suc_chua']}.
        Danh sách phòng: {', '.join([f'{r.name}({r.suc_chua})' for r in rooms])}.

        Hãy đề xuất 1 phòng tốt nhất và lý do ngắn gọn, và viết lại thông tin đặt phòng.
        """

        try:
            ai_response = self.env['dat_phong'].sudo()._call_gemini_api(prompt)
            result_text = f"AI Gemini gợi ý:\n{ai_response}\n\nPhòng được chọn (dựa trên dữ liệu hệ thống): {candidate_name}"
            self.write({'goi_y_ai': result_text, 'phong_id': candidate_id})
        except BaseException as e:
            self.write({'goi_y_ai': f'Lỗi khi lấy gợi ý AI: {str(e)}. Vui lòng thử lại sau.'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_dat_phong_theo_goi_y(self):
        """Đặt phòng theo gợi ý AI - tạo booking tự động"""
        if not self.phong_id:
            raise exceptions.UserError('AI chưa gợi ý phòng nào. Vui lòng nhấn "Lấy gợi ý AI" trước.')
        
        # Parse thời gian từ yêu cầu
        parse = self._parse_text_request(self.yeu_cau_text)
        if not (parse['date'] and parse['start_time'] and parse['duration']):
            raise exceptions.UserError('Không thể trích xuất thời gian từ yêu cầu. Vui lòng kiểm tra lại định dạng.')
        
        # Tính thời gian bắt đầu và kết thúc
        start = datetime(year=parse['date'].year, month=parse['date'].month, day=parse['date'].day,
                         hour=parse['start_time'][0], minute=parse['start_time'][1])
        end = start + timedelta(minutes=parse['duration'])
        
        # Tạo booking
        try:
            new_booking = self.env['dat_phong'].sudo().create({
                'phong_id': self.phong_id.id,
                'nguoi_muon_id': self.nguoi_muon_id.id,
                'thoi_gian_muon_du_kien': start,
                'thoi_gian_tra_du_kien': end,
                'trang_thai': 'chờ_duyệt',
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'dat_phong',
                'view_mode': 'form',
                'res_id': new_booking.id,
                'target': 'current',
            }
        except exceptions.ValidationError as e:
            raise exceptions.UserError(f'Lỗi tạo booking: {str(e)}')
        except Exception as e:
            raise exceptions.UserError(f'Lỗi hệ thống khi đặt phòng: {str(e)}')
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
