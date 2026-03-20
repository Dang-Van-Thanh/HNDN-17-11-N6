from odoo import models, fields, api, exceptions

class DatPhongGeminiWizard(models.TransientModel):
    _name = 'dat_phong.gemini.wizard'
    _description = 'Gợi ý và đặt phòng họp bằng AI Gemini'

    thoi_gian_muon_du_kien = fields.Datetime(string='Thời gian mượn dự kiến', required=True)
    thoi_gian_tra_du_kien = fields.Datetime(string='Thời gian trả dự kiến', required=True)
    suc_chua = fields.Integer(string='Sức chứa tối thiểu', required=True, default=2)
    nguoi_muon_id = fields.Many2one('nhan_vien', string='Người mượn', required=True)
    phong_id = fields.Many2one('quan_ly_phong_hop', string='Phòng đề xuất')
    goi_y_ai = fields.Text(string='Gợi ý AI Gemini')

    @api.onchange('thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien', 'suc_chua')
    def onchange_suggest(self):
        if not (self.thoi_gian_muon_du_kien and self.thoi_gian_tra_du_kien and self.suc_chua):
            return

        data = self.env['dat_phong'].suggest_room_for_time_capacity(
            self.thoi_gian_muon_du_kien,
            self.thoi_gian_tra_du_kien,
            self.suc_chua,
        )

        self.goi_y_ai = data.get('ai_report', '')
        # Nếu có phòng phù hợp, chọn phòng nhỏ nhất đủ điều kiện để đề xuất
        if data.get('choices'):
            rooms = data.get('choices')
            self.phong_id = rooms.sorted(key=lambda r: r.suc_chua)[0] if rooms else False

    def action_confirm_booking(self):
        if not self.phong_id:
            raise exceptions.UserError('Vui lòng chọn phòng họp trước khi đặt.')
        if self.thoi_gian_muon_du_kien >= self.thoi_gian_tra_du_kien:
            raise exceptions.UserError('Thời gian trả phải lớn hơn thời gian mượn.')

        new_booking = self.env['dat_phong'].create({
            'phong_id': self.phong_id.id,
            'nguoi_muon_id': self.nguoi_muon_id.id,
            'thoi_gian_muon_du_kien': self.thoi_gian_muon_du_kien,
            'thoi_gian_tra_du_kien': self.thoi_gian_tra_du_kien,
            'trang_thai': 'chờ_duyệt',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dat_phong',
            'view_mode': 'form',
            'res_id': new_booking.id,
        }
