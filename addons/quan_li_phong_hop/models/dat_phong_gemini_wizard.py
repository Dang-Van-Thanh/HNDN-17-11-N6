from odoo import models, fields, api, exceptions

class DatPhongGeminiWizard(models.TransientModel):
    _name = 'dat_phong.gemini.wizard'
    _description = 'Gợi ý đặt phòng họp bằng AI Gemini'

    thoi_gian_muon_du_kien = fields.Datetime(string='Thời gian mượn dự kiến', required=True)
    thoi_gian_tra_du_kien = fields.Datetime(string='Thời gian trả dự kiến', required=True)
    suc_chua = fields.Integer(string='Sức chứa tối thiểu', required=True, default=2)
    nguoi_muon_id = fields.Many2one('nhan_vien', string='Người mượn', required=True)
    goi_y_ai = fields.Text(string='Gợi ý AI Gemini')

    def action_get_ai_suggestion(self):
        """Gọi AI Gemini để lấy gợi ý chi tiết"""
        if not (self.thoi_gian_muon_du_kien and self.thoi_gian_tra_du_kien and self.suc_chua):
            self.goi_y_ai = 'Vui lòng điền đầy đủ thông tin trước khi yêu cầu gợi ý AI.'
            return

        try:
            data = self.env['dat_phong'].sudo().suggest_room_for_time_capacity(
                self.thoi_gian_muon_du_kien,
                self.thoi_gian_tra_du_kien,
                self.suc_chua,
            )

            self.goi_y_ai = data.get('ai_report', 'Không thể lấy gợi ý từ AI. Vui lòng thử lại.')
        except Exception as e:
            self.goi_y_ai = f'Lỗi khi lấy gợi ý AI: {str(e)}. Vui lòng thử lại sau.'
