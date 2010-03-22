from django.contrib.contenttypes.models import ContentType
from django.db import models

from tagging.managers import ModelTaggedItemManager

from jflow.db.instdata.converters import convert
from jflow.db.instdata.settings import DEFAULT_VENDOR_FOR_SITE


class DataIdManager(ModelTaggedItemManager):
    
    def ct_from_type(self, type):
        '''
        Return content type object from type name
        '''
        app_label = self.model._meta.app_label
        return ContentType.objects.get(name = type, app_label = app_label)
    
    def ctmodel(self, type):
        if type:
            try:
                ct = self.ct_from_type(type)
                return ct, ct.model_class()
            except:
                raise ValueError('Data type %s not available' % type)
        else:
            return None,None
    
    def for_type(self, type):
        try:
            ct = self.ct_from_type(type)
        except:
            return self.none()
        return self.filter(content_type = ct)
    
    def get_or_create(self, **kwargs):
        '''
        Override get_or_create.
        
        kwargs must contain:
            code
            country
            default_vendor
        
        Optional
            type
            tags         
        '''
        code = kwargs.pop('code',None)
        if not code:
            raise ValueError('cannot add data id, code not specified')
        id, created = super(DataIdManager,self).get_or_create(code = code)
        
        if created:
            return self.create(id, **kwargs), True
        else:
            return self.modify(id, **kwargs), False
        
    def create(self, id,
               commit = True,
               type = None,
               country = None,
               default_vendor = None, **kwargs):
        '''
        Create a new instrument
        '''
        ct, model = self.ctmodel(type)
        id.default_vendor  = convert('vendor', default_vendor or DEFAULT_VENDOR_FOR_SITE)
        id.country = convert('country', country)
        if ct:
            id._new_content = model.objects.create(id, commit = commit, **kwargs)
            id.content_type = ct
        if commit:
            id.save()
        return id
        
    def modify(self, id,
               commit = True,
               type = None,
               country = None,
               default_vendor = None, **kwargs):
        ct, model = self.ctmodel(type)
        if default_vendor:
            id.default_vendor  = convert('vendor', default_vendor)
        if country:
            id.country = convert('country', country)
        if ct:
            inst = id.instrument
            if inst:
                inst.delete()
            id._new_content = model.objects.create(id, commit = commit, **kwargs)
            id.content_type = ct
            id.object_id    = inst.id
            id.curncy       = inst.ccy()
        if commit:
            id.save()
        return id
        
        
class InstrumentManager(models.Manager):
    pass

class SecurityManager(InstrumentManager):
    
    def create(self, id, ISIN = '', CUSIP = '', SEDOL = '', exchange = '', **kwargs):
        exchange = convert('exchange', exchange)
        return self.model(dataid = id, code = id.code,
                          ISIN = ISIN, CUSIP = CUSIP,
                          SEDOL = SEDOL, exchange = exchange)

class EtfManager(SecurityManager):
    
    def create(self, id, curncy = '', multiplier = 1,
               settlement_delay = 2, **kwargs):
        obj = super(EtfManager,self).create(id, **kwargs)
        obj.curncy = convert('curncy',curncy)
        obj.multiplier = multiplier or 1
        obj.settlement_delay = settlement_delay
        obj.save()
        return obj
    
class EquityManager(SecurityManager):
    
    def create(self, id, curncy = '', multiplier = 1,
               settlement_delay = 2,  security_type = 1,
               sector = None, sectorid = None,
               group = None, groupid = None,
               industry_code = None, **kwargs):
        if not industry_code:
            #TODO remove thid import and obtain moel from self.model 
            from jflow.db.instdata.models import IndustryCode as secmodel
            #secmodel = self.model._name_map.get('industry_code')[0]
            industry_code = secmodel.objects.create(sector, sectorid, group, groupid)
        obj = super(EquityManager,self).create(id, **kwargs)
        obj.industry_code = industry_code
        obj.curncy = convert('curncy',curncy)
        obj.multiplier = multiplier or 1
        obj.settlement_delay = settlement_delay
        obj.security_type = convert('security_type',security_type)
        obj.save()
        return obj
    
                

class FundManager(SecurityManager):
    
    def create(self, id, curncy = '', multiplier = 1,
               settlement_delay = 2,  security_type = 1,
               **kwargs):
        obj = super(FundManager,self).create(id, **kwargs)
        obj.curncy = convert('curncy',curncy)
        obj.multiplier = multiplier or 1
        obj.settlement_delay = settlement_delay
        obj.security_type = convert('security_type',security_type)
        obj.save()
        return obj
    
class BondManager(SecurityManager):
    
    def create(self, id,
               curncy            = '',
               country           = '',
               bondclass__code   = None,
               collateral_type   = None,
               announce_date     = None,
               first_settle_date = None,
               first_coupon_date = None,
               accrual_date      = None,
               maturity_date     = None,
               multiplier        = 0.01,
               settlement_delay  = 3,
               **kwargs):
        obj = super(BondManager,self).create(id, **kwargs)
        obj.announce_date       = convert('bonddate',announce_date)
        obj.first_settle_date   = convert('bonddate',first_settle_date)
        obj.first_coupon_date   = convert('bonddate',first_coupon_date)
        obj.accrual_date        = convert('bonddate',accrual_date)
        obj.maturity_date       = convert('bonddate',maturity_date)
        obj.collateral_type     = convert('collateral',collateral_type)
        
        ccy = convert('curncy',curncy)
        country = convert('country',country)
        bck = {}
        isu = {}
        for k,v in kwargs.items():
            ks = k.split('__')
            if len(ks) == 2:
                if ks[0] == 'bondclass':
                    bck[ks[1]] = v
                elif ks[0] == 'issuer':
                    isu[ks[1]] = v
                    
        obj.bond_class          = convert('bondclass',
                                          bondclass__code,
                                          curncy=ccy,
                                          country=country,
                                          **bck)
        
        obj.multiplier = multiplier or 1
        obj.settlement_delay = settlement_delay
        obj.save()
        return obj

class DecompManager(models.Manager):
    
    def for_object(self, id, code = None, dt = None):
        code = code or id.code
        v = self.filter(dataid = id, code = code)
        if not dt:
            v = v.latest
        return v.composition
        

class IndustryCodeManager(models.Manager):
    
    def create(self, sector, sectorid, group, groupid):
        if sector and sectorid and group and groupid:
            try:
                sid  = int(sectorid)
                gid  = int(groupid)
            except:
                return None
            sector, created = self.get_or_create(id = sid, code = sector)
            group, created = self.get_or_create(id = gid, code = group)
            group.parent = sector
            group.save()
            return group
        else:
            return None

