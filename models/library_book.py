# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.tools.translate import _


class BaseArchive(models.AbstractModel):
    _name = 'base.archive'

    active = fields.Boolean(default=True)

    def do_archive(self):
        for record in self:
            record.active = not record.active


class LibraryBook(models.Model):
    _name = 'library.book'
    _inherit = ['base.archive']
    _description = 'Library Book'
    _rec_name = 'short_name'
    _order = 'date_release desc, name'
    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'Book title must be uniquie.'),
        ('positive_page', 'CHECK(pages>0)', 'No of pages must be positive')
    ]

    name = fields.Char('Title', required=True)
    short_name = fields.Char('Short Title', required=True)
    date_release = fields.Date('Release Date')
    author_ids = fields.Many2many('res.partner', string='Authors')
    notes = fields.Text('Internal Notes')
    state = fields.Selection([
        ('draft', 'Not Available'),
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('lost', 'Lost')],
        'State', default="draft")
    description = fields.Html('Description')
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print?')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages')
    reader_rating = fields.Float('Reader Average Rating', digits=(14,4))
    cost_price = fields.Float('Book Cost', digits='Book Price')
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price')
    publisher_id = fields.Many2one('res.partner', string='Publsiher')
    author_ids = fields.Many2many('res.partner', string='Authors')
    category_id = fields.Many2one('library.book.category')
    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
    )
    parent_id = fields.Many2one('res.partner', string='Publisher')
    publisher_city = fields.Char('Publisher City', related='parent_id.city', readonly=True)
    ref_doc_id = fields.Reference(selection='_referencable_models', string='Reference Document')


    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].search([('field_id.name', '=', 'message_ids')])
        return [(x.model, x.name) for x in models]

    @api.depends('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delta = today - book.date_release
                book.age_days = delta.days
            else:
                book.age_days = 0

    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = d

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        operator_map = {
            '>': '<', '>=': '<=',
            '<': '>', '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]



    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if record.date_release and record.date_release > fields.Date.today():
                raise models.ValidationError(
                    'Release date must be in the past.'
                )

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed=[
            ('draft', 'available'),
            ('available', 'borrowed'),
            ('borrowed', 'available'),
            ('available', 'lost'),
            ('borrowed', 'lost'),
            ('lost', 'available')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                msg = _('Moving from %s to %s is not allowed') % (book.state, new_state)
                raise UserError(msg)

    def make_available(self):
        self.change_state('available')

    def make_borrowed(self):
        self.change_state('borrowed')

    def make_lost(self):
        self.change_state('lost')

    def get_all_library_members(self):
        library_member_model = self.env['library.member']
        all_members = library_member_model.search([])
        print("ALL MEBMERS:", all_members)
        return True

    def create_categories(self):
        categ1 = {
            'name': 'Child category 1',
            'description': 'Description for child 1'
        }
        categ2 = {
            'name': 'Child category 2',
            'description': 'Description for child 2'
        }
        parent_category_val = {
            'name': 'Parent category',
            'description': 'Description for parent category',
            'child_ids': [
                (0, 0, categ1),
                (0, 0, categ2),
            ]
        }
        recrod = self.env['library.book.category'].create(parent_category_val)
        return True

    def change_release_date(self):
        self.ensure_one()
        self.date_release = fields.Date.today()
        

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = 'name'

    published_book_ids = fields.One2many('library.book', 'publisher_id', string='Published Books')
    authored_book_ids = fields.Many2many('library.book', string='Authored Books')
    count_books = fields.Integer( 'Number of Authored Books', compute='_compute_count_books')

    @api.depends('authored_book_ids')
    def _compute_count_books(self):
        for r in self:
            r.count_books = len(r.authored_books_ids)
    

class LibraryMember(models.Model):
    _name = 'library.member'
    _inherits = {'res.partner': 'partner+id'}
    
    partner_id = fields.Many2one('res.patner', ondelete='cascade')
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of birth')

