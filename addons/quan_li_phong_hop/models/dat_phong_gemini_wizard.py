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
    phong_phu_hop_ids = fields.Many2many('quan_ly_phong_hop', string='Phòng phù hợp', readonly=True)
    so_phong_phu_hop = fields.Integer(string='Số phòng phù hợp', compute='_compute_so_phong_phu_hop', store=True)

    @api.depends('phong_phu_hop_ids')
    def _compute_so_phong_phu_hop(self):
        for record in self:
            record.so_phong_phu_hop = len(record.phong_phu_hop_ids)

    @api.onchange('thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien', 'suc_chua')
    def onchange_suggest(self):
        """Cập nhật nhanh danh sách phòng phù hợp khi thay đổi điều kiện"""
        if not (self.thoi_gian_muon_du_kien and self.thoi_gian_tra_du_kien and self.suc_chua):
            self.phong_id = False
            self.phong_phu_hop_ids = [(5, 0, 0)]  # Clear all
            return

        # Chỉ lọc phòng, không gọi AI để tránh chậm
        rooms = self.env['dat_phong']._get_available_rooms(
            self.thoi_gian_muon_du_kien,
            self.thoi_gian_tra_du_kien,
            self.suc_chua,
        )

        # Cập nhật danh sách phòng phù hợp
        self.phong_phu_hop_ids = [(6, 0, rooms.ids)] if rooms else [(5, 0, 0)]

        # Chọn phòng đề xuất mặc định (phòng nhỏ nhất đủ điều kiện)
        if rooms:
            self.phong_id = rooms.sorted(key=lambda r: r.suc_chua)[0]
        else:
            self.phong_id = False

    def action_get_ai_suggestion(self):
        """Gọi AI Gemini để lấy gợi ý chi tiết"""
        if not (self.thoi_gian_muon_du_kien and self.thoi_gian_tra_du_kien and self.suc_chua):
            self.goi_y_ai = 'Vui lòng điền đầy đủ thông tin trước khi yêu cầu gợi ý AI.'
            return

        data = self.env['dat_phong'].suggest_room_for_time_capacity(
            self.thoi_gian_muon_du_kien,
            self.thoi_gian_tra_du_kien,
            self.suc_chua,
        )

        self.goi_y_ai = data.get('ai_report', 'Không thể lấy gợi ý từ AI. Vui lòng thử lại.')

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
