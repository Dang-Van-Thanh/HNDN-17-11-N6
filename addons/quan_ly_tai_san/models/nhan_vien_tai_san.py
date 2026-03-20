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

            open_phieus = self.env['phieu_muon'].search(
                [
                    ('nhan_vien_id', '=', record.id),
                    ('tai_san_id', 'in', laptop_assets.ids),
                    ('state', 'in', ['draft', 'approved']),
                ]
            )
            for phieu in open_phieus:
                if phieu.state == 'approved':
                    # action_done sẽ cập nhật tai_san và lịch sử
                    phieu.action_done()
                else:
                    # bỏ qua chuyển thành done nếu mới draft
                    phieu.state = 'done'

    @api.model
    def create(self, vals):
        record = super(NhanVien, self).create(vals)
        if record.trang_thai == 'DangLam':
            record._allocate_laptop_and_create_phieu_muon()
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
                elif current == 'NghiViec':
                    record._reclaim_assets_and_close_phi_muon()

        return result
