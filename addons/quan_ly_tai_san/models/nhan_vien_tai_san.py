from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError


class NhanVien(models.Model):
    _inherit = 'nhan_vien'

    def _get_available_laptop(self):
        loai_laptop = self.env['loai_tai_san'].search([('ten_loai_tai_san', 'ilike', 'Laptop')], limit=1)
        if not loai_laptop:
            raise UserError('Không tìm thấy loại tài sản Laptop. Vui lòng thêm loại tài sản Laptop trước khi cấp phát.')

        laptop = self.env['tai_san'].search(
            [
                ('loai_tai_san_id', '=', loai_laptop.id),
                ('trang_thai', '=', 'CatGiu'),
            ],
            order='ma_tai_san asc',
            limit=1,
        )
        if not laptop:
            raise UserError('Không còn laptop sẵn sàng. Vui lòng bổ sung tài sản Laptop.')
        return laptop

    def _allocate_laptop_and_create_phieu_muon(self):
        for record in self:
            if record.trang_thai != 'DangLam':
                continue

            existing_laptop = self.env['tai_san'].search(
                [
                    ('nguoi_su_dung_id', '=', record.id),
                    ('loai_tai_san_id.ten_loai_tai_san', 'ilike', 'Laptop'),
                ],
                limit=1,
            )
            if existing_laptop:
                continue

            laptop = record._get_available_laptop()

            now = fields.Datetime.now()
            phi_muon = self.env['phieu_muon'].create({
                'nhan_vien_id': record.id,
                'tai_san_id': laptop.id,
                'ngay_muon_du_kien': now,
                'ngay_tra_du_kien': (fields.Datetime.to_datetime(now) + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S'),
            })

            # Duyệt phiếu mượn đồng thời cập nhật trạng thái tài sản.
            phi_muon.action_approve()

    def _reclaim_assets_and_close_phi_muon(self):
        for record in self:
            laptop_assets = self.env['tai_san'].search(
                [
                    ('nguoi_su_dung_id', '=', record.id),
                    ('loai_tai_san_id.ten_loai_tai_san', 'ilike', 'Laptop'),
                ]
            )
            if laptop_assets:
                laptop_assets.write({'trang_thai': 'CatGiu', 'nguoi_su_dung_id': False})

            # Hủy tất cả phiếu mượn của nhân viên (không chỉ laptop)
            open_phieus = self.env['phieu_muon'].search(
                [
                    ('nhan_vien_id', '=', record.id),
                    ('state', 'in', ['draft', 'approved']),
                ]
            )
            for phieu in open_phieus:
                if phieu.state == 'approved':
                    # Gọi action_cancel để hủy phiếu mượn
                    phieu.action_cancel()
                else:
                    # Nếu draft thì chuyển trạng thái thành cancelled
                    phieu.state = 'cancelled'

            # Thu hồi đặt phòng họp thuộc trạng thái chờ/đã duyệt/đang sử dụng khi nhân viên nghỉ việc
            booking_records = self.env['dat_phong'].search([
                ('nguoi_muon_id', '=', record.id),
                ('trang_thai', 'in', ['chờ_duyệt', 'đã_duyệt', 'đang_sử_dụng']),
            ])
            for booking in booking_records:
                if booking.trang_thai == 'đang_sử_dụng':
                    try:
                        booking.tra_phong()
                    except Exception:
                        booking.write({'trang_thai': 'đã_hủy'})
                else:
                    booking.write({'trang_thai': 'đã_hủy'})

    def _book_meeting_room(self):
        for record in self:
            if record.trang_thai != 'DangLam':
                continue

            # Chọn phòng họp Trống có sức chứa tối thiểu >=2 và nhỏ nhất
            rooms = self.env['quan_ly_phong_hop'].search([
                ('trang_thai', '=', 'Trống'),
                ('suc_chua', '>=', 2),
            ], order='suc_chua asc')
            room = rooms[:1] if rooms else False

            if not room:
                raise UserError('Không tìm thấy phòng họp Trống với sức chứa >=2. Vui lòng thêm hoặc thanh toán phòng phù hợp.')

            now = fields.Datetime.now()
            start = fields.Datetime.to_datetime(now) + timedelta(days=1)
            end = start + timedelta(minutes=30)

            booking = self.env['dat_phong'].create({
                'phong_id': room.id,
                'nguoi_muon_id': record.id,
                'thoi_gian_muon_du_kien': start.strftime('%Y-%m-%d %H:%M:%S'),
                'thoi_gian_tra_du_kien': end.strftime('%Y-%m-%d %H:%M:%S'),
            })

            # Tự động duyệt, chờ bắt đầu
            booking.xac_nhan_duyet_phong()

    @api.model
    def create(self, vals):
        record = super(NhanVien, self).create(vals)
        if record.trang_thai == 'DangLam':
            record._allocate_laptop_and_create_phieu_muon()
            record._book_meeting_room()
        return record

    def write(self, vals):
        old_values = {rec.id: rec.trang_thai for rec in self}
        result = super(NhanVien, self).write(vals)

        for record in self:
            previous = old_values.get(record.id)
            current = vals.get('trang_thai', record.trang_thai)

            if previous != current:
                if current == 'DangLam':
                    record._allocate_laptop_and_create_phieu_muon()
                    record._book_meeting_room()
                elif current == 'NghiViec':
                    record._reclaim_assets_and_close_phi_muon()

        return result
