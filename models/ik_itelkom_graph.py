from odoo import api, fields, models, exceptions, http
from datetime import date
from dateutil.relativedelta import relativedelta
import xlwt
import io
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot
import numpy
import cherrypy
import logging
_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class GraficosAvanzados(models.Model):
    _name = 'itelkom.graphs'
    _description = 'Graficos avanzados'

    name = fields.Char(string='Nombre',required=True)
    graph_modelo = fields.Many2one('ir.model',string='Modelo',required=True)
    data_lines = fields.One2many(comodel_name='itelkom.graphs.data',inverse_name='graph_id',string='Datos')
    filter_lines = fields.One2many(comodel_name='itelkom.graphs.filter',inverse_name='graph_id',string='Filtros')
    graph_graph = fields.Binary(string='Grafico',readonly=True)
    graph_graph_filename = fields.Char(string='graph Filename',readonly=True)
    graph_report = fields.Binary(string='Reporte',readonly=True)
    graph_report_filename = fields.Char(string='Reporte Filename',readonly=True)
    plottype = fields.Selection([('bar','Barras'),('line','Linea'),('pie','Pie'),('point','Puntos')],string='Tipo de grafico',default='bar')
    update = fields.Selection([('nunca','Nunca'),('hour', 'Cada hora'),('12hours', 'Cada 12 horas'),('day', 'Cada dia'),('semana', 'Cada semana'),('mes', 'Cada mes')],string='Ejecucion automatica',default='nunca')

    def create_plot(self,title,ylabel,xlabel, xdata, ydata):
        image = BytesIO()
        pyplot.plot(xdata, ydata)
        pyplot.ylabel = ylabel
        pyplot.xlabel = xlabel
        pyplot.title = title
        pyplot.savefig(image, format='png')
        return base64.encodestring(image.getvalue())

    def action_agregate_data(self):
        if not self.id:
            raise exceptions.ValidationError("Primero debe guardar la busqueda para agregar nuevos datos.")
        data_model = self.env['itelkom.graphs.data']
        d_size = len(data_model.search([('graph_id','=',self.id)]).ids)
        data_model.create({'graph_id': self.id, 'name': 'Dato', 'secuence': d_size+1})

    def action_agregate_filter(self):
        if not self.id:
            raise exceptions.ValidationError("Primero debe guardar la busqueda para agregar nuevos datos.")
        filter_model = self.env['itelkom.graphs.filter']
        filter_model.create({'graph_id': self.id, 'condition': '='})

    def action_generate_graph(self):
        r_model = self.env[self.graph_modelo.model]

        filters = []
        abc = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP','AQ','AR','AS','AT','AU','AV','AW','AX','AY','AZ','BA','BB','BC','BD','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP','BQ','BR','BS','BT','BU','BV','BW','BX','BY','BZ']

        if len(self.data_lines) < 1 or len(self.data_lines) >= len(abc):
            raise exceptions.ValidationError("Se ha superado el limite de datos: "+len(abc))

        #Read Filters  
        for filt in self.filter_lines:
            if filt.data_1.name:
                value = filt.searchvalue
                condition = filt.condition
                if condition == 'False' or condition == 'True':
                    condition = ('!=' if condition=='True' else '=')
                    value = False
                elif condition == 'inicia':
                    condition = 'ilike'
                    value = str(value) + '%'
                elif condition == 'in' and filt.searchvalue and filt.searchvalue2:
                    value = []
                    value.append(filt.searchvalue)
                    if filt.searchvalue2: value.append(filt.searchvalue2)
                    if filt.searchvalue3: value.append(filt.searchvalue3)
                    if filt.searchvalue4: value.append(filt.searchvalue4)
                    if filt.searchvalue5: value.append(filt.searchvalue5)
                f = filt.data_1.name + ('.'+filt.data_2.name if filt.data_2 else '') + ('.'+filt.data_3.name if filt.data_3 else '') + ('.'+filt.data_4.name if filt.data_4 else '') + ('.'+filt.data_5.name if filt.data_5 else '')
                if not f or not condition:
                    raise exceptions.ValidationError("Complete los datos de todos los filtros.")
                filters.append([f,condition,value])
            else:
                raise exceptions.ValidationError("Complete los datos de todos los filtros.")
        #Searching data using filters 
        result = False
        if filters:
            result = r_model.search(filters)
            if not result:
                raise exceptions.ValidationError("No se encontro ningun resultado con los filtros datos.")
        else:
            raise exceptions.ValidationError("No se ha detectado ningun filtro.")
            
        for dt in self.data_lines:
            if not dt.name or not dt.data_1.name:
                raise exceptions.ValidationError("Favor llene el nombre y los datos que desea tener en el Grafico.")

        graph = []
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format({'font_size': '12px'})
        head = workbook.add_format({'align': 'center', 'bold': True,'font_size':'20px'})
        txt = workbook.add_format({'font_size': '10px'})
        row = 1
        for d in self.data_lines:
            if d.secuence > 0 and d.secuence < len(abc):
                sheet.write(abc[d.secuence - 1]+'1', d.name, head)

        ylabel = ""
        xlabel = ""
        xdata = []
        ydata = []
        data = False

        for r in result:
            row += 1
            idx = False
            idy = False
            for dt in self.data_lines:
                if dt.secuence > 0 and dt.secuence < len(abc):
                    data = False
                    if dt.data_5.name: data = r[dt.data_1.name][dt.data_2.name][dt.data_3.name][dt.data_4.name][dt.data_5.name]
                    elif dt.data_4.name: data = r[dt.data_1.name][dt.data_2.name][dt.data_3.name][dt.data_4.name]
                    elif dt.data_3.name: data = r[dt.data_1.name][dt.data_2.name][dt.data_3.name]
                    elif dt.data_2.name: data = r[dt.data_1.name][dt.data_2.name]
                    elif dt.data_1.name: data = r[dt.data_1.name]
                    if data:
                        sheet.write(abc[dt.secuence - 1]+str(row), data, txt)
                    if dt.graph_data_type and dt.graph_data_type == 'xdata' and not idx:
                        if not xlabel: xlabel = dt.name
                        if data not in xdata: 
                            xdata.append(data)
                            ydata.append(0)
                        idx = xdata.index(data)
                    if dt.graph_data_type and dt.graph_data_type == 'ydata' and idx >= 0 and not idy:
                        try:
                            if dt.operation != 'count': 
                                data = float(data)
                        except ValueError:
                            raise exceptions.ValidationError("Solo son aceptados valores numericos para el eje Y.")
                        if not ylabel: ylabel = dt.name
                        if dt.operation == 'sum': ydata[idx] += data
                        elif dt.operation == 'count': ydata[idx] += 1
                        elif dt.operation == 'rest': ydata[idx] -= data
                        else: raise exceptions.ValidationError("Operacion no aceptada.")
                        idy = True
        workbook.close()
        output.seek(0)
        self.graph_report = base64.encodestring(output.getvalue())
        self.graph_report_filename = self.name + "_" + str(date.today()) + ".xlsx"
        output.close()
        self.graph_graph = self.create_plot(self.name, ylabel, xlabel, xdata, ydata)
        self.graph_graph_filename = self.name + "_" + str(date.today()) + ".png"
 
class GraficosAvanzadosData(models.Model):
    _name = 'itelkom.graphs.data'
    _description = 'Datos Graficos avanzados'

    name = fields.Char(string='Nombre',required=True)
    graph_id = fields.Many2one('itelkom.graphs',string='Grafico')
    secuence = fields.Integer(string='Secuencia', required=True)
    graph_data_type = fields.Selection([('xdata', 'Eje X'),('ydata', 'Eje Y')],string='Tipo')
    operation = fields.Selection([('sum', 'Sumar'),('count', 'Contar'),('rest','Restar'),('group','Agrupar')],string='Operacion',default='group')
    data_1 = fields.Many2one('ir.model.fields',string='Dato 1')
    relation_1 = fields.Char(related='data_1.relation',store=False,string='Relacion')
    data_2 = fields.Many2one('ir.model.fields',string='Dato 2')
    relation_2 = fields.Char(related='data_2.relation',store=False,string='Relacion')
    data_3 = fields.Many2one('ir.model.fields',string='Dato 3')
    relation_3 = fields.Char(related='data_3.relation',store=False,string='Relacion')
    data_4 = fields.Many2one('ir.model.fields',string='Dato 4')
    relation_4 = fields.Char(related='data_4.relation',store=False,string='Relacion')
    data_5 = fields.Many2one('ir.model.fields',string='Dato 5')
    model_base = fields.Integer(related='graph_id.graph_modelo.id',store=False,string='Model Base')

class GraficosAvanzadosFilter(models.Model):
    _name = 'itelkom.graphs.filter'
    _description = 'Filtros Graficos avanzados'

    graph_id = fields.Many2one('itelkom.graphs',string='Grafico')
    data_1 = fields.Many2one('ir.model.fields',string='Dato 1')
    relation_1 = fields.Char(related='data_1.relation',store=False,string='Relacion')
    data_2 = fields.Many2one('ir.model.fields',string='Dato 2')
    relation_2 = fields.Char(related='data_2.relation',store=False,string='Relacion')
    data_3 = fields.Many2one('ir.model.fields',string='Dato 3')
    relation_3 = fields.Char(related='data_3.relation',store=False,string='Relacion')
    data_4 = fields.Many2one('ir.model.fields',string='Dato 4')
    relation_4 = fields.Char(related='data_4.relation',store=False,string='Relacion')
    data_5 = fields.Many2one('ir.model.fields',string='Dato 5')
    condition = fields.Selection([('=', 'Igual'),('!=', 'Diferente'),('>', 'Mayor'),('<', 'Menor'),('>=', 'Mayor igual'),('<=', 'Menor igual'),('ilike', 'Contiene'),('inicia', 'Inicia con'),('in','Es uno de'),('True', 'Verdadero'),('False', 'Falso')],string='Condicion')
    searchvalue = fields.Char(string='Valor a buscar')
    searchvalue2 = fields.Char(string='Valor a buscar 2')
    searchvalue3 = fields.Char(string='Valor a buscar 3')
    searchvalue4 = fields.Char(string='Valor a buscar 4')
    searchvalue5 = fields.Char(string='Valor a buscar 5')
    model_base = fields.Integer(related='graph_id.graph_modelo.id',store=False,string='Model Base')


