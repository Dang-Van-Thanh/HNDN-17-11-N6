from odoo import models, fields, api, exceptions
import re

class DatPhongGeminiWizard(models.TransientModel):
    _name = 'dat_phong.gemini.wizard'
    _description = 'Gợi ý đặt phòng họp bằng AI Gemini'

    yeu_cau_text = fields.Text(string='Yêu cầu đặt phòng (ví dụ: Tôi cần phòng họp cho 10 người vào ngày 21/4 và có thời gian 30 phút)', required=True)
    nguoi_muon_id = fields.Many2one('nhan_vien', string='Người mượn', required=True)
    goi_y_ai = fields.Text(string='Gợi ý AI Gemini', readonly=True)
    phong_id = fields.Many2one('quan_ly_phong_hop', string='Phòng đề xuất', readonly=True)

    def action_get_ai_suggestion(self):
        """Gọi AI Gemini để phân tích yêu cầu và gợi ý phòng"""
        if not self.yeu_cau_text:
            self.goi_y_ai = 'Vui lòng nhập yêu cầu đặt phòng.'
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        # Prompt để AI phân tích và gợi ý
        prompt = f"""
        Phân tích yêu cầu đặt phòng sau: "{self.yeu_cau_text}"
        
        Hãy:
        1. Trích xuất thông tin: số người, ngày, thời gian bắt đầu, thời lượng.
        2. Gợi ý phòng họp phù hợp từ danh sách có sẵn.
        3. Trả về định dạng:
        Phòng đề xuất: [Tên phòng]
        Lý do: [Lý do ngắn gọn]
        """

        try:
            ai_response = self.env['dat_phong'].sudo()._call_gemini_api(prompt)
            self.goi_y_ai = ai_response

            # Parse để tìm phòng đề xuất
            match = re.search(r'Phòng đề xuất:\s*([^\n]+)', ai_response, re.IGNORECASE)
            if match:
                room_name = match.group(1).strip()
                room = self.env['quan_ly_phong_hop'].sudo().search([('name', 'ilike', room_name)], limit=1)
                if room:
                    self.phong_id = room.id
                else:
                    self.goi_y_ai += '\n\nKhông tìm thấy phòng phù hợp trong hệ thống.'
            else:
                self.goi_y_ai += '\n\nAI không đề xuất phòng cụ thể.'

        except BaseException as e:
            self.goi_y_ai = f'Lỗi khi lấy gợi ý AI: {str(e)}. Vui lòng thử lại sau.'

        # Reload wizard để hiển thị kết quả
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_dat_phong_theo_goi_y(self):
        """Đặt phòng theo gợi ý AI"""
        if not self.phong_id:
            raise exceptions.UserError('AI chưa gợi ý phòng nào. Vui lòng nhấn "Lấy gợi ý AI" trước.')
        
        # Parse thời gian từ yêu cầu (đơn giản, giả sử có ngày và thời gian)
        # Đây là placeholder, có thể cải thiện bằng AI parse thêm
        # Giả sử user nhập có ngày, parse để set thời gian
        # Nhưng để đơn giản, raise error yêu cầu nhập thời gian cụ thể
        raise exceptions.UserError('Chức năng đặt phòng tự động chưa hoàn thiện. Vui lòng sử dụng form đặt phòng thông thường với thông tin từ gợi ý AI.')

        # Nếu parse được, tạo booking
        # new_booking = self.env['dat_phong'].create({...})
        # return action to view booking

        # Reload wizard để hiển thị kết quả
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
