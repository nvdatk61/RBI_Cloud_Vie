import os
from builtins import int
from itertools import count

from django.core.wsgi import get_wsgi_application
from numpy.lib.function_base import vectorize
from reportlab.platypus.para import paragraphEngine
from scipy.io.arff.arffread import r_wcomattrval
from sympy.functions.elementary.complexes import im

os.environ['DJANGO_SETTINGS_MODULE'] = 'RbiCloud.settings'
application = get_wsgi_application()

from PIL.PngImagePlugin import _idat
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, render_to_response
from django.http import Http404, HttpResponse
from cloud import models
from dateutil.relativedelta import relativedelta
from cloud.process.RBI import DM_CAL, CA_CAL, pofConvert
from datetime import datetime
from cloud.process.WebUI import location
from cloud.process.WebUI import roundData
from cloud.process.File import export_data
from cloud.process.WebUI import date2Str
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from cloud.process.File import import_data as ExcelImport
from cloud.process.RBI import fastCalulate as ReCalculate
from django.db.models import Q
from cloud.regularverification.regular import REGULAR
import threading
from cloud.regularverification import subscribe
# import paho.mqtt.client as mqtt
from cloud.regularverification import subscribe_thingsboard

from django.views.decorators.csrf import csrf_protect
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from cloud.tokens import gen_token
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from cloud.process.RBI import Postgresql as DAL_CAL
from cloud.process.RBI import CA_Flammable
from cloud.process.RBI import ToxicConsequenceArea
from cloud.process.RBI import FinancialCOF,Detail_DM_CAL
from django.contrib.auth import login
import time
from django.http import JsonResponse


# Create your views here.

################ Base ####################
def Base_citizen(request):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    if request.session['kind'] == 'citizen':
        return render(request, 'BaseUI/BaseCitizen/baseCitizen.html', {'info': request.session, 'count': count})


def base_manager(request):
    try:
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
    except:
        Http404
    return render(request, 'BaseUI/BaseManager/baseManager.html', {'count': count})


def base_business(request):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    if request.session['kind'] == 'factory':
        return render(request, 'BaseUI/BaseFacility/baseBusiness.html', {'info': request.session, 'count': count})


def business_home(request):
    return render(request, 'BaseUI/BaseFacility/baseFacility.html')


def base_equipment(request):
    return render(request, 'BaseUI/BaseFacility/baseEquipment.html')


def base_component(request):
    return render(request, 'BaseUI/BaseFacility/baseComponent.html')


def base_proposal(request):
    return render(request, 'BaseUI/BaseFacility/baseProposal.html')


def base_risksummary(request):
    return render(request, 'BaseUI/BaseFacility/baseRiskSummary.html')


def base_designcode(request):
    return render(request, 'BaseUI/BaseFacility/baseDesigncode.html')


def base_manufacture(request):
    return render(request, 'FacilityUI/manufacture/manufactureListDisplay.html')


################## 404 Error ###########################
def handler404(request):
    return render(request, '404/404.html', locals())


################ Inspection Plan #######################
def ListInpsectionPlan():
    inspection = models.InspecPlan.objects.all()
    try:
        data = []
        for a in inspection:
            obj = {}
            obj["ID"] = a.id
            obj["InspecPlanName"] = a.inspectionplanname
            obj["InspecPlanDate"] = a.inspectionplandate
            data.append(obj)
    except Exception as e:
        print(e)
    return data


def ListInspectionCoverage(planID):
    inspection = models.InspecPlan.objects.get(id=planID)
    inspecCover = models.InspectionCoverage.objects.filter(planid_id=planID)
    data = []
    for a in inspecCover:
        obj = {}
        obj["ID"] = planID
        obj["InpsecName"] = inspection.inspectionplanname
        obj["InspecDate"] = inspection.inspectionplandate
        obj["NameEquipment"] = models.EquipmentMaster.objects.get(equipmentid=a.equipmentid_id).equipmentnumber
        obj["NameComponent"] = models.ComponentMaster.objects.get(componentid=a.componentid_id).componentnumber
        data.append(obj)
    return data


def InspectionPlanDetail(request, planID):  # hàm chính
    return 0


def ListNormalProposalFofInpsection(siteID, facilityID, equimentID):
    # site = models.Sites.objects.get(siteID=3)
    data = []
    tank = [8, 9, 12, 13, 14, 15]
    datarw = []  # kiem tra id proposal co ton tai trong bang RwDamageMechanism
    datapof = []  # kiem tra id  proposal co ton tai trong bang RwFullPof
    componenttypeID = 0
    rwdamAll = models.RwDamageMechanism.objects.all()
    rwfullpofAll = models.RwFullPof.objects.all()
    for a in rwdamAll:
        array = a.id_dm_id
        datarw.append(array)
    for b in rwfullpofAll:
        brray = b.id_id
        datapof.append(brray)
    try:
        if facilityID:
            faci = models.Facility.objects.filter(facilityid=facilityID)
            for f in faci:
                if equimentID:
                    equip = models.EquipmentMaster.objects.filter(equipmentid=equimentID)
                else:
                    equip = models.EquipmentMaster.objects.filter(facilityid_id=f.facilityid)
                for e in equip:
                    comp = models.ComponentMaster.objects.filter(equipmentid_id=e.equipmentid)
                    equiptype = models.EquipmentType.objects.get(equipmenttypeid=e.equipmenttypeid_id)
                    desi = models.DesignCode.objects.get(designcodeid=e.designcodeid_id)
                    for c in comp:
                        pros = models.RwAssessment.objects.filter(componentid_id=c.componentid)
                        comptype = models.ComponentType.objects.get(componenttypeid=c.componenttypeid_id)
                        for p in pros:
                            componenttypeID = comptype.componenttypeid
                            obj = {}
                            rwequip = models.RwEquipment.objects.get(id_id=p.id)
                            rwcomponent = models.RwComponent.objects.get(id_id=p.id)
                            rwstream = models.RwStream.objects.get(id_id=p.id)
                            rwmaterial = models.RwMaterial.objects.get(id_id=p.id)
                            rwcoat = models.RwCoating.objects.get(id_id=p.id)
                            obj['ID'] = p.id
                            obj['ConponentName'] = c.componentname
                            obj['ConponentNumber'] = c.componentnumber
                            obj['EquipmentNumber'] = e.equipmentnumber
                            obj['CommissionDate'] = e.commissiondate
                            obj['Site'] = "SITE"
                            obj['Facility'] = f.facilityname
                            if (p.id in datapof):
                                rwfullpof = models.RwFullPof.objects.get(id_id=p.id)
                                obj['API1'] = rwfullpof.thinningap1
                                obj['API2'] = rwfullpof.thinningap2
                                obj['API3'] = rwfullpof.thinningap3
                                obj['RLI'] = rwfullpof.rli
                            else:
                                obj['API1'] = "None"
                                obj['API2'] = "None"
                                obj['API3'] = "None"
                                obj['RLI'] = "None"
                            obj['AssessmentName'] = p.proposalname
                            obj['AssessmentDate'] = p.assessmentdate
                            obj['RiskAnalysisPeriod'] = p.riskanalysisperiod
                            obj['EquipmentType'] = equiptype.equipmenttypename
                            obj['ComponentType'] = comptype.componenttypename
                            if (p.id in datarw):
                                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=p.id)
                                obj['InspectionDueDate'] = rwdam.inspduedate
                            else:
                                obj['InspectionDueDate'] = "None"
                            obj['DesignCode'] = desi.designcode
                            # Equipment Properties
                            obj['adminControlUpset'] = rwequip.adminupsetmanagement
                            obj['ContainsDeadlegs'] = rwequip.containsdeadlegs
                            obj['PresenceofSulphides'] = rwequip.presencesulphideso2
                            obj['SteamedOut'] = rwequip.steamoutwaterflush
                            obj['ThermalHistory'] = rwequip.thermalhistory
                            obj['SystemManagementFactor'] = rwequip.managementfactor
                            obj['PWHT'] = rwequip.pwht
                            obj['PressurisationControlled'] = rwequip.pressurisationcontrolled
                            obj['PresenceofSulphidesShutdow'] = rwequip.presencesulphideso2shutdown
                            obj['OnlineMonitoring'] = rwequip.onlinemonitoring
                            obj['minreqtemperaturepressurisation'] = rwequip.minreqtemperaturepressurisation
                            obj['MFTF'] = rwequip.materialexposedtoclext
                            obj['CylicOper'] = rwequip.cyclicoperation
                            obj['LOM'] = rwequip.lineronlinemonitoring
                            obj['Downtime'] = rwequip.downtimeprotectionused
                            obj['EquOper'] = rwequip.yearlowestexptemp
                            obj['EquipmentVolume'] = rwequip.volume
                            obj['ExternalEnvironment'] = rwequip.interfacesoilwater
                            obj['InterfaceSoilWater'] = rwequip.externalenvironment
                            obj['HeatTraced'] = rwequip.heattraced
                            obj['Highly'] = rwequip.highlydeadleginsp
                            # Component
                            obj['MinimumMeasuredThickness'] = rwcomponent.currentthickness
                            obj['NominalThickness'] = rwcomponent.nominalthickness
                            obj['NominalDiameter'] = rwcomponent.nominaldiameter
                            obj['MinRequiredThickness'] = rwcomponent.minreqthickness
                            obj['CurrentCorrosionRate'] = rwcomponent.currentcorrosionrate
                            obj['PresenceCracks'] = rwcomponent.crackspresent
                            obj['PreviousFailure'] = rwcomponent.previousfailures
                            obj['DFDI'] = rwcomponent.damagefoundinspection
                            obj['HFICI'] = rwcomponent.highlyinjectioninsp
                            obj['PIMP'] = 0
                            # obj['TrampElements'] = rwcomponent.trampelements
                            obj['TrampElements'] = 0
                            obj['DeltaFATT'] = rwcomponent.deltafatt
                            obj['CylicLoadingConnectedwithin1525m'] = rwcomponent.cyclicloadingwitin15_25m
                            obj['MaximumBrinnellHardnessofWeld'] = rwcomponent.brinnelhardness
                            obj['NumberofFittingsonPipe'] = rwcomponent.numberpipefittings
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['PipeCondition'] = rwcomponent.pipecondition
                            obj['VASD'] = rwcomponent.shakingdetected
                            obj['shakingamount'] = rwcomponent.shakingamount
                            obj['correctiveaction'] = rwcomponent.correctiveaction
                            obj['branchdiameter'] = rwcomponent.branchdiameter
                            obj['complexityprotrusion'] = rwcomponent.complexityprotrusion
                            # Stream
                            obj['maxoperatingtemperature'] = rwstream.maxoperatingtemperature
                            obj['minoperatingtemperature'] = rwstream.minoperatingtemperature
                            obj['minoperatingpressure'] = rwstream.minoperatingpressure
                            obj['criticalexposuretemperature'] = rwstream.criticalexposuretemperature
                            obj['aminesolution'] = rwstream.aminesolution
                            obj['naohconcentration'] = rwstream.naohconcentration
                            obj['h2sinwater'] = rwstream.h2sinwater
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['flowrate'] = rwstream.flowrate
                            obj['waterph'] = rwstream.waterph
                            obj['ToxicConstituents'] = rwstream.toxicconstituent
                            obj['releasefluidpercenttoxic'] = rwstream.releasefluidpercenttoxic
                            obj['PCH'] = rwstream.hydrogen
                            obj['PHA'] = rwstream.hydrofluoric
                            obj['exposuretoamine'] = rwstream.exposuretoamine
                            obj['PresenceCyanides'] = rwstream.cyanide
                            obj['h2spartialpressure'] = rwstream.h2spartialpressure
                            obj['ESBC'] = rwstream.exposedtosulphur
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EnvironmentCH2S'] = rwstream.h2s
                            obj['ECCAC'] = rwstream.caustic
                            obj['co3concentration'] = rwstream.co3concentration
                            obj['chloride'] = rwstream.chloride
                            obj['APDO'] = rwstream.aqueousoperation
                            obj['APDSD'] = rwstream.aqueousshutdown
                            # Material
                            obj['designtemperature'] = rwmaterial.designtemperature
                            obj['allowablestress'] = rwcomponent.allowablestress  # Component
                            obj['designpressure'] = rwmaterial.designpressure
                            obj['temper'] = rwmaterial.temper
                            obj['sulfurcontent'] = rwmaterial.sulfurcontent
                            obj['sigmaphase'] = rwmaterial.sigmaphase
                            obj['referencetemperature'] = rwmaterial.referencetemperature
                            obj['NickelAlloy'] = rwmaterial.nickelbased
                            obj['costfactor'] = rwmaterial.costfactor
                            obj['heattreatment'] = rwmaterial.heattreatment
                            obj['corrosionallowance'] = rwmaterial.corrosionallowance
                            obj['Chromium'] = rwmaterial.chromemoreequal12
                            obj['CoLAS'] = rwmaterial.carbonlowalloy
                            obj['AusteniticSteel'] = rwmaterial.austenitic
                            # Coating
                            obj['InternalCoating'] = rwcoat.internalcoating
                            obj['ExternalCoating'] = rwcoat.externalcoating
                            obj['externalcoatingdate'] = rwcoat.externalcoatingdate
                            obj['externalcoatingquality'] = rwcoat.externalcoatingquality
                            obj['supportMaterial'] = rwcoat.supportconfignotallowcoatingmaint
                            obj['InternalLining'] = rwcoat.internallining
                            obj['internallinertype'] = rwcoat.internallinertype
                            obj['internallinercondition'] = rwcoat.internallinercondition
                            obj['internalcladding'] = rwcoat.internalcladding
                            obj['claddingcorrosionrate'] = rwcoat.claddingcorrosionrate
                            obj['externalinsulation'] = rwcoat.externalinsulation
                            obj['externalinsulationtype'] = rwcoat.externalinsulationtype
                            obj['insulationcondition'] = rwcoat.insulationcondition
                            obj['insulationcontainschloride'] = rwcoat.insulationcontainschloride
                            if not componenttypeID in tank:
                                data.append(obj)
        else:
            faci = models.Facility.objects.filter(siteid_id=siteID)
            for f in faci:
                equip = models.EquipmentMaster.objects.filter(facilityid_id=f.facilityid)
                for e in equip:
                    comp = models.ComponentMaster.objects.filter(equipmentid_id=e.equipmentid)
                    equiptype = models.EquipmentType.objects.get(equipmenttypeid=e.equipmenttypeid_id)
                    desi = models.DesignCode.objects.get(designcodeid=e.designcodeid_id)
                    for c in comp:
                        pros = models.RwAssessment.objects.filter(componentid_id=c.componentid)
                        comptype = models.ComponentType.objects.get(componenttypeid=c.componenttypeid_id)
                        componenttypeID = comptype.componenttypeid
                        for p in pros:
                            obj = {}
                            rwequip = models.RwEquipment.objects.get(id_id=p.id)
                            rwcomponent = models.RwComponent.objects.get(id_id=p.id)
                            rwstream = models.RwStream.objects.get(id_id=p.id)
                            rwmaterial = models.RwMaterial.objects.get(id_id=p.id)
                            rwcoat = models.RwCoating.objects.get(id_id=p.id)
                            obj['ID'] = p.id
                            obj['ConponentName'] = c.componentname
                            obj['ConponentNumber'] = c.componentnumber
                            obj['EquipmentNumber'] = e.equipmentnumber
                            obj['CommissionDate'] = e.commissiondate
                            obj['Site'] = "SITE"
                            obj['Facility'] = f.facilityname
                            if (p.id in datapof):
                                rwfullpof = models.RwFullPof.objects.get(id_id=p.id)
                                obj['API1'] = rwfullpof.thinningap1
                                obj['API2'] = rwfullpof.thinningap2
                                obj['API3'] = rwfullpof.thinningap3
                                obj['RLI'] = rwfullpof.rli
                            else:
                                obj['API1'] = "None"
                                obj['API2'] = "None"
                                obj['API3'] = "None"
                                obj['RLI'] = "None"
                            obj['AssessmentName'] = p.proposalname
                            obj['AssessmentDate'] = p.assessmentdate
                            obj['RiskAnalysisPeriod'] = p.riskanalysisperiod
                            obj['EquipmentType'] = equiptype.equipmenttypename
                            obj['ComponentType'] = comptype.componenttypename
                            if (p.id in datarw):
                                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=p.id)
                                obj['InspectionDueDate'] = rwdam.inspduedate
                            else:
                                obj['InspectionDueDate'] = "None"
                            obj['DesignCode'] = desi.designcode
                            # Equipment Properties
                            obj['adminControlUpset'] = rwequip.adminupsetmanagement
                            obj['ContainsDeadlegs'] = rwequip.containsdeadlegs
                            obj['PresenceofSulphides'] = rwequip.presencesulphideso2
                            obj['SteamedOut'] = rwequip.steamoutwaterflush
                            obj['ThermalHistory'] = rwequip.thermalhistory
                            obj['SystemManagementFactor'] = rwequip.managementfactor
                            obj['PWHT'] = rwequip.pwht
                            obj['PressurisationControlled'] = rwequip.pressurisationcontrolled
                            obj['PresenceofSulphidesShutdow'] = rwequip.presencesulphideso2shutdown
                            obj['OnlineMonitoring'] = rwequip.onlinemonitoring
                            obj['minreqtemperaturepressurisation'] = rwequip.minreqtemperaturepressurisation
                            obj['MFTF'] = rwequip.materialexposedtoclext
                            obj['CylicOper'] = rwequip.cyclicoperation
                            obj['LOM'] = rwequip.lineronlinemonitoring
                            obj['Downtime'] = rwequip.downtimeprotectionused
                            obj['EquOper'] = rwequip.yearlowestexptemp
                            obj['EquipmentVolume'] = rwequip.volume
                            obj['ExternalEnvironment'] = rwequip.interfacesoilwater
                            obj['InterfaceSoilWater'] = rwequip.externalenvironment
                            obj['HeatTraced'] = rwequip.heattraced
                            obj['Highly'] = rwequip.highlydeadleginsp
                            # Component
                            obj['MinimumMeasuredThickness'] = rwcomponent.currentthickness
                            obj['NominalThickness'] = rwcomponent.nominalthickness
                            obj['NominalDiameter'] = rwcomponent.nominaldiameter
                            obj['MinRequiredThickness'] = rwcomponent.minreqthickness
                            obj['CurrentCorrosionRate'] = rwcomponent.currentcorrosionrate
                            obj['PresenceCracks'] = rwcomponent.crackspresent
                            obj['PreviousFailure'] = rwcomponent.previousfailures
                            obj['DFDI'] = rwcomponent.damagefoundinspection
                            obj['HFICI'] = rwcomponent.highlyinjectioninsp
                            obj['PIMP'] = 0
                            # obj['TrampElements'] = rwcomponent.trampelements
                            obj['TrampElements'] = 0
                            obj['DeltaFATT'] = rwcomponent.deltafatt
                            obj['CylicLoadingConnectedwithin1525m'] = rwcomponent.cyclicloadingwitin15_25m
                            obj['MaximumBrinnellHardnessofWeld'] = rwcomponent.brinnelhardness
                            obj['NumberofFittingsonPipe'] = rwcomponent.numberpipefittings
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['PipeCondition'] = rwcomponent.pipecondition
                            obj['VASD'] = rwcomponent.shakingdetected
                            obj['shakingamount'] = rwcomponent.shakingamount
                            obj['correctiveaction'] = rwcomponent.correctiveaction
                            obj['branchdiameter'] = rwcomponent.branchdiameter
                            obj['complexityprotrusion'] = rwcomponent.complexityprotrusion
                            # Stream
                            obj['maxoperatingtemperature'] = rwstream.maxoperatingtemperature
                            obj['minoperatingtemperature'] = rwstream.minoperatingtemperature
                            obj['minoperatingpressure'] = rwstream.minoperatingpressure
                            obj['criticalexposuretemperature'] = rwstream.criticalexposuretemperature
                            obj['aminesolution'] = rwstream.aminesolution
                            obj['naohconcentration'] = rwstream.naohconcentration
                            obj['h2sinwater'] = rwstream.h2sinwater
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['flowrate'] = rwstream.flowrate
                            obj['waterph'] = rwstream.waterph
                            obj['ToxicConstituents'] = rwstream.toxicconstituent
                            obj['releasefluidpercenttoxic'] = rwstream.releasefluidpercenttoxic
                            obj['PCH'] = rwstream.hydrogen
                            obj['PHA'] = rwstream.hydrofluoric
                            obj['exposuretoamine'] = rwstream.exposuretoamine
                            obj['PresenceCyanides'] = rwstream.cyanide
                            obj['h2spartialpressure'] = rwstream.h2spartialpressure
                            obj['ESBC'] = rwstream.exposedtosulphur
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EnvironmentCH2S'] = rwstream.h2s
                            obj['ECCAC'] = rwstream.caustic
                            obj['co3concentration'] = rwstream.co3concentration
                            obj['chloride'] = rwstream.chloride
                            obj['APDO'] = rwstream.aqueousoperation
                            obj['APDSD'] = rwstream.aqueousshutdown
                            # Material
                            obj['designtemperature'] = rwmaterial.designtemperature
                            obj['allowablestress'] = rwcomponent.allowablestress  # Component
                            obj['designpressure'] = rwmaterial.designpressure
                            obj['temper'] = rwmaterial.temper
                            obj['sulfurcontent'] = rwmaterial.sulfurcontent
                            obj['sigmaphase'] = rwmaterial.sigmaphase
                            obj['referencetemperature'] = rwmaterial.referencetemperature
                            obj['NickelAlloy'] = rwmaterial.nickelbased
                            obj['costfactor'] = rwmaterial.costfactor
                            obj['heattreatment'] = rwmaterial.heattreatment
                            obj['corrosionallowance'] = rwmaterial.corrosionallowance
                            obj['Chromium'] = rwmaterial.chromemoreequal12
                            obj['CoLAS'] = rwmaterial.carbonlowalloy
                            obj['AusteniticSteel'] = rwmaterial.austenitic
                            # Coating
                            obj['InternalCoating'] = rwcoat.internalcoating
                            obj['ExternalCoating'] = rwcoat.externalcoating
                            obj['externalcoatingdate'] = rwcoat.externalcoatingdate
                            obj['externalcoatingquality'] = rwcoat.externalcoatingquality
                            obj['supportMaterial'] = rwcoat.supportconfignotallowcoatingmaint
                            obj['InternalLining'] = rwcoat.internallining
                            obj['internallinertype'] = rwcoat.internallinertype
                            obj['internallinercondition'] = rwcoat.internallinercondition
                            obj['internalcladding'] = rwcoat.internalcladding
                            obj['claddingcorrosionrate'] = rwcoat.claddingcorrosionrate
                            obj['externalinsulation'] = rwcoat.externalinsulation
                            obj['externalinsulationtype'] = rwcoat.externalinsulationtype
                            obj['insulationcondition'] = rwcoat.insulationcondition
                            obj['insulationcontainschloride'] = rwcoat.insulationcontainschloride
                            if not componenttypeID in tank:
                                data.append(obj)
    except Exception as e:
        print(e)
    return data


def ListTankProposalForInpsection(siteID, facilityID, equimentID):
    dataTank = []
    tank = [8, 9, 12, 13, 14, 15]
    datarw = []  # kiem tra id proposal co ton tai trong bang RwDamageMechanism
    datapof = []  # kiem tra id  proposal co ton tai trong bang RwFullPof
    componenttypeID = 0
    try:
        if facilityID:
            faci = models.Facility.objects.filter(facilityid=facilityID)
            for f in faci:
                if equimentID:
                    equip = models.EquipmentMaster.objects.filter(facilityid_id=f.facilityid)
                else:
                    equip = models.EquipmentMaster.objects.filter(equipmentid=equimentID)
                for e in equip:
                    comp = models.ComponentMaster.objects.filter(equipmentid_id=e.equipmentid)
                    equiptype = models.EquipmentType.objects.get(equipmenttypeid=e.equipmenttypeid_id)
                    desi = models.DesignCode.objects.get(designcodeid=e.designcodeid_id)
                    for c in comp:
                        pros = models.RwAssessment.objects.filter(componentid_id=c.componentid)
                        comptype = models.ComponentType.objects.get(componenttypeid=c.componenttypeid_id)
                        componenttypeID = comptype.componenttypeid
                        for p in pros:
                            obj = {}
                            rwequip = models.RwEquipment.objects.get(id_id=p.id)
                            rwcomponent = models.RwComponent.objects.get(id_id=p.id)
                            rwstream = models.RwStream.objects.get(id_id=p.id)
                            rwmaterial = models.RwMaterial.objects.get(id_id=p.id)
                            rwcoat = models.RwCoating.objects.get(id_id=p.id)
                            obj['ID'] = p.id
                            obj['ConponentName'] = c.componentname
                            obj['ConponentNumber'] = c.componentnumber
                            obj['EquipmentNumber'] = e.equipmentnumber
                            obj['CommissionDate'] = e.commissiondate
                            obj['Site'] = "SITE"
                            obj['Facility'] = f.facilityname
                            if (p.id in datapof):
                                rwfullpof = models.RwFullPof.objects.get(id_id=p.id)
                                obj['API1'] = rwfullpof.thinningap1
                                obj['API2'] = rwfullpof.thinningap2
                                obj['API3'] = rwfullpof.thinningap3
                                obj['RLI'] = rwfullpof.rli
                            else:
                                obj['API1'] = "None"
                                obj['API2'] = "None"
                                obj['API3'] = "None"
                                obj['RLI'] = "None"
                            obj['AssessmentName'] = p.proposalname
                            obj['AssessmentDate'] = p.assessmentdate
                            obj['RiskAnalysisPeriod'] = p.riskanalysisperiod
                            obj['EquipmentType'] = equiptype.equipmenttypename
                            obj['ComponentType'] = comptype.componenttypename
                            if (p.id in datarw):
                                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=p.id)
                                obj['InspectionDueDate'] = rwdam.inspduedate
                            else:
                                obj['InspectionDueDate'] = "None"
                            obj['DesignCode'] = desi.designcode
                            # Equipment Properties
                            obj['adminControlUpset'] = rwequip.adminupsetmanagement
                            obj['ContainsDeadlegs'] = rwequip.containsdeadlegs
                            obj['PresenceofSulphides'] = rwequip.presencesulphideso2
                            obj['SteamedOut'] = rwequip.steamoutwaterflush
                            obj['ThermalHistory'] = rwequip.thermalhistory
                            obj['SystemManagementFactor'] = rwequip.managementfactor
                            obj['PWHT'] = rwequip.pwht
                            obj['PressurisationControlled'] = rwequip.pressurisationcontrolled
                            obj['PresenceofSulphidesShutdow'] = rwequip.presencesulphideso2shutdown
                            obj['OnlineMonitoring'] = rwequip.onlinemonitoring
                            obj['minreqtemperaturepressurisation'] = rwequip.minreqtemperaturepressurisation
                            obj['MFTF'] = rwequip.materialexposedtoclext
                            obj['CylicOper'] = rwequip.cyclicoperation
                            obj['LOM'] = rwequip.lineronlinemonitoring
                            obj['Downtime'] = rwequip.downtimeprotectionused
                            obj['EquOper'] = rwequip.yearlowestexptemp
                            obj['EquipmentVolume'] = rwequip.volume
                            obj['ExternalEnvironment'] = rwequip.interfacesoilwater
                            obj['InterfaceSoilWater'] = rwequip.externalenvironment
                            obj['HeatTraced'] = rwequip.heattraced
                            obj['Highly'] = rwequip.highlydeadleginsp
                            # Component
                            obj['MinimumMeasuredThickness'] = rwcomponent.currentthickness
                            obj['NominalThickness'] = rwcomponent.nominalthickness
                            obj['NominalDiameter'] = rwcomponent.nominaldiameter
                            obj['MinRequiredThickness'] = rwcomponent.minreqthickness
                            obj['CurrentCorrosionRate'] = rwcomponent.currentcorrosionrate
                            obj['PresenceCracks'] = rwcomponent.crackspresent
                            obj['PreviousFailure'] = rwcomponent.previousfailures
                            obj['DFDI'] = rwcomponent.damagefoundinspection
                            obj['HFICI'] = rwcomponent.highlyinjectioninsp
                            obj['PIMP'] = 0
                            # obj['TrampElements'] = rwcomponent.trampelements
                            obj['TrampElements'] = 0
                            obj['DeltaFATT'] = rwcomponent.deltafatt
                            obj['CylicLoadingConnectedwithin1525m'] = rwcomponent.cyclicloadingwitin15_25m
                            obj['MaximumBrinnellHardnessofWeld'] = rwcomponent.brinnelhardness
                            obj['NumberofFittingsonPipe'] = rwcomponent.numberpipefittings
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['PipeCondition'] = rwcomponent.pipecondition
                            obj['VASD'] = rwcomponent.shakingdetected
                            obj['shakingamount'] = rwcomponent.shakingamount
                            obj['correctiveaction'] = rwcomponent.correctiveaction
                            obj['branchdiameter'] = rwcomponent.branchdiameter
                            obj['complexityprotrusion'] = rwcomponent.complexityprotrusion
                            # Stream
                            obj['maxoperatingtemperature'] = rwstream.maxoperatingtemperature
                            obj['minoperatingtemperature'] = rwstream.minoperatingtemperature
                            obj['minoperatingpressure'] = rwstream.minoperatingpressure
                            obj['criticalexposuretemperature'] = rwstream.criticalexposuretemperature
                            obj['aminesolution'] = rwstream.aminesolution
                            obj['naohconcentration'] = rwstream.naohconcentration
                            obj['h2sinwater'] = rwstream.h2sinwater
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['flowrate'] = rwstream.flowrate
                            obj['waterph'] = rwstream.waterph
                            obj['ToxicConstituents'] = rwstream.toxicconstituent
                            obj['releasefluidpercenttoxic'] = rwstream.releasefluidpercenttoxic
                            obj['PCH'] = rwstream.hydrogen
                            obj['PHA'] = rwstream.hydrofluoric
                            obj['exposuretoamine'] = rwstream.exposuretoamine
                            obj['PresenceCyanides'] = rwstream.cyanide
                            obj['h2spartialpressure'] = rwstream.h2spartialpressure
                            obj['ESBC'] = rwstream.exposedtosulphur
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EnvironmentCH2S'] = rwstream.h2s
                            obj['ECCAC'] = rwstream.caustic
                            obj['co3concentration'] = rwstream.co3concentration
                            obj['chloride'] = rwstream.chloride
                            obj['APDO'] = rwstream.aqueousoperation
                            obj['APDSD'] = rwstream.aqueousshutdown
                            # Material
                            obj['designtemperature'] = rwmaterial.designtemperature
                            obj['allowablestress'] = rwcomponent.allowablestress  # Component
                            obj['designpressure'] = rwmaterial.designpressure
                            obj['temper'] = rwmaterial.temper
                            obj['sulfurcontent'] = rwmaterial.sulfurcontent
                            obj['sigmaphase'] = rwmaterial.sigmaphase
                            obj['referencetemperature'] = rwmaterial.referencetemperature
                            obj['NickelAlloy'] = rwmaterial.nickelbased
                            obj['costfactor'] = rwmaterial.costfactor
                            obj['heattreatment'] = rwmaterial.heattreatment
                            obj['corrosionallowance'] = rwmaterial.corrosionallowance
                            obj['Chromium'] = rwmaterial.chromemoreequal12
                            obj['CoLAS'] = rwmaterial.carbonlowalloy
                            obj['AusteniticSteel'] = rwmaterial.austenitic
                            # Coating
                            obj['InternalCoating'] = rwcoat.internalcoating
                            obj['ExternalCoating'] = rwcoat.externalcoating
                            obj['externalcoatingdate'] = rwcoat.externalcoatingdate
                            obj['externalcoatingquality'] = rwcoat.externalcoatingquality
                            obj['supportMaterial'] = rwcoat.supportconfignotallowcoatingmaint
                            obj['InternalLining'] = rwcoat.internallining
                            obj['internallinertype'] = rwcoat.internallinertype
                            obj['internallinercondition'] = rwcoat.internallinercondition
                            obj['internalcladding'] = rwcoat.internalcladding
                            obj['claddingcorrosionrate'] = rwcoat.claddingcorrosionrate
                            obj['externalinsulation'] = rwcoat.externalinsulation
                            obj['externalinsulationtype'] = rwcoat.externalinsulationtype
                            obj['insulationcondition'] = rwcoat.insulationcondition
                            obj['insulationcontainschloride'] = rwcoat.insulationcontainschloride
                            if not componenttypeID in tank:
                                dataTank.append(obj)
        else:
            faci = models.Facility.objects.filter(siteid_id=siteID)
            for f in faci:
                equip = models.EquipmentMaster.objects.filter(facilityid_id=f.facilityid)
                for e in equip:
                    comp = models.ComponentMaster.objects.filter(equipmentid_id=e.equipmentid)
                    equiptype = models.EquipmentType.objects.get(equipmenttypeid=e.equipmenttypeid_id)
                    desi = models.DesignCode.objects.get(designcodeid=e.designcodeid_id)
                    for c in comp:
                        pros = models.RwAssessment.objects.filter(componentid_id=c.componentid)
                        comptype = models.ComponentType.objects.get(componenttypeid=c.componenttypeid_id)
                        componenttypeID = comptype.componenttypeid
                        for p in pros:
                            obj = {}
                            rwequip = models.RwEquipment.objects.get(id_id=p.id)
                            rwcomponent = models.RwComponent.objects.get(id_id=p.id)
                            rwstream = models.RwStream.objects.get(id_id=p.id)
                            rwmaterial = models.RwMaterial.objects.get(id_id=p.id)
                            rwcoat = models.RwCoating.objects.get(id_id=p.id)
                            obj['ID'] = p.id
                            obj['ConponentName'] = c.componentname
                            obj['ConponentNumber'] = c.componentnumber
                            obj['EquipmentNumber'] = e.equipmentnumber
                            obj['CommissionDate'] = e.commissiondate
                            obj['Site'] = "SITE"
                            obj['Facility'] = f.facilityname
                            if (p.id in datapof):
                                rwfullpof = models.RwFullPof.objects.get(id_id=p.id)
                                obj['API1'] = rwfullpof.thinningap1
                                obj['API2'] = rwfullpof.thinningap2
                                obj['API3'] = rwfullpof.thinningap3
                                obj['RLI'] = rwfullpof.rli
                            else:
                                obj['API1'] = "None"
                                obj['API2'] = "None"
                                obj['API3'] = "None"
                                obj['RLI'] = "None"
                            obj['AssessmentName'] = p.proposalname
                            obj['AssessmentDate'] = p.assessmentdate
                            obj['RiskAnalysisPeriod'] = p.riskanalysisperiod
                            obj['EquipmentType'] = equiptype.equipmenttypename
                            obj['ComponentType'] = comptype.componenttypename
                            if (p.id in datarw):
                                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=p.id)
                                obj['InspectionDueDate'] = rwdam.inspduedate
                            else:
                                obj['InspectionDueDate'] = "None"
                            obj['DesignCode'] = desi.designcode
                            # Equipment Properties
                            obj['adminControlUpset'] = rwequip.adminupsetmanagement
                            obj['ContainsDeadlegs'] = rwequip.containsdeadlegs
                            obj['PresenceofSulphides'] = rwequip.presencesulphideso2
                            obj['SteamedOut'] = rwequip.steamoutwaterflush
                            obj['ThermalHistory'] = rwequip.thermalhistory
                            obj['SystemManagementFactor'] = rwequip.managementfactor
                            obj['PWHT'] = rwequip.pwht
                            obj['PressurisationControlled'] = rwequip.pressurisationcontrolled
                            obj['PresenceofSulphidesShutdow'] = rwequip.presencesulphideso2shutdown
                            obj['OnlineMonitoring'] = rwequip.onlinemonitoring
                            obj['minreqtemperaturepressurisation'] = rwequip.minreqtemperaturepressurisation
                            obj['MFTF'] = rwequip.materialexposedtoclext
                            obj['CylicOper'] = rwequip.cyclicoperation
                            obj['LOM'] = rwequip.lineronlinemonitoring
                            obj['Downtime'] = rwequip.downtimeprotectionused
                            obj['EquOper'] = rwequip.yearlowestexptemp
                            obj['EquipmentVolume'] = rwequip.volume
                            obj['ExternalEnvironment'] = rwequip.interfacesoilwater
                            obj['InterfaceSoilWater'] = rwequip.externalenvironment
                            obj['HeatTraced'] = rwequip.heattraced
                            obj['Highly'] = rwequip.highlydeadleginsp
                            # Component
                            obj['MinimumMeasuredThickness'] = rwcomponent.currentthickness
                            obj['NominalThickness'] = rwcomponent.nominalthickness
                            obj['NominalDiameter'] = rwcomponent.nominaldiameter
                            obj['MinRequiredThickness'] = rwcomponent.minreqthickness
                            obj['CurrentCorrosionRate'] = rwcomponent.currentcorrosionrate
                            obj['PresenceCracks'] = rwcomponent.crackspresent
                            obj['PreviousFailure'] = rwcomponent.previousfailures
                            obj['DFDI'] = rwcomponent.damagefoundinspection
                            obj['HFICI'] = rwcomponent.highlyinjectioninsp
                            obj['PIMP'] = 0
                            # obj['TrampElements'] = rwcomponent.trampelements
                            obj['TrampElements'] = 0
                            obj['DeltaFATT'] = rwcomponent.deltafatt
                            obj['CylicLoadingConnectedwithin1525m'] = rwcomponent.cyclicloadingwitin15_25m
                            obj['MaximumBrinnellHardnessofWeld'] = rwcomponent.brinnelhardness
                            obj['NumberofFittingsonPipe'] = rwcomponent.numberpipefittings
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['JointTypeofBranch'] = rwcomponent.branchjointtype
                            obj['PipeCondition'] = rwcomponent.pipecondition
                            obj['VASD'] = rwcomponent.shakingdetected
                            obj['shakingamount'] = rwcomponent.shakingamount
                            obj['correctiveaction'] = rwcomponent.correctiveaction
                            obj['branchdiameter'] = rwcomponent.branchdiameter
                            obj['complexityprotrusion'] = rwcomponent.complexityprotrusion
                            # Stream
                            obj['maxoperatingtemperature'] = rwstream.maxoperatingtemperature
                            obj['minoperatingtemperature'] = rwstream.minoperatingtemperature
                            obj['minoperatingpressure'] = rwstream.minoperatingpressure
                            obj['criticalexposuretemperature'] = rwstream.criticalexposuretemperature
                            obj['aminesolution'] = rwstream.aminesolution
                            obj['naohconcentration'] = rwstream.naohconcentration
                            obj['h2sinwater'] = rwstream.h2sinwater
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['MEFMSCC'] = rwstream.materialexposedtoclint
                            obj['flowrate'] = rwstream.flowrate
                            obj['waterph'] = rwstream.waterph
                            obj['ToxicConstituents'] = rwstream.toxicconstituent
                            obj['releasefluidpercenttoxic'] = rwstream.releasefluidpercenttoxic
                            obj['PCH'] = rwstream.hydrogen
                            obj['PHA'] = rwstream.hydrofluoric
                            obj['exposuretoamine'] = rwstream.exposuretoamine
                            obj['PresenceCyanides'] = rwstream.cyanide
                            obj['h2spartialpressure'] = rwstream.h2spartialpressure
                            obj['ESBC'] = rwstream.exposedtosulphur
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EAGTA'] = rwstream.exposedtogasamine
                            obj['EnvironmentCH2S'] = rwstream.h2s
                            obj['ECCAC'] = rwstream.caustic
                            obj['co3concentration'] = rwstream.co3concentration
                            obj['chloride'] = rwstream.chloride
                            obj['APDO'] = rwstream.aqueousoperation
                            obj['APDSD'] = rwstream.aqueousshutdown
                            # Material
                            obj['designtemperature'] = rwmaterial.designtemperature
                            obj['allowablestress'] = rwcomponent.allowablestress  # Component
                            obj['designpressure'] = rwmaterial.designpressure
                            obj['temper'] = rwmaterial.temper
                            obj['sulfurcontent'] = rwmaterial.sulfurcontent
                            obj['sigmaphase'] = rwmaterial.sigmaphase
                            obj['referencetemperature'] = rwmaterial.referencetemperature
                            obj['NickelAlloy'] = rwmaterial.nickelbased
                            obj['costfactor'] = rwmaterial.costfactor
                            obj['heattreatment'] = rwmaterial.heattreatment
                            obj['corrosionallowance'] = rwmaterial.corrosionallowance
                            obj['Chromium'] = rwmaterial.chromemoreequal12
                            obj['CoLAS'] = rwmaterial.carbonlowalloy
                            obj['AusteniticSteel'] = rwmaterial.austenitic
                            # Coating
                            obj['InternalCoating'] = rwcoat.internalcoating
                            obj['ExternalCoating'] = rwcoat.externalcoating
                            obj['externalcoatingdate'] = rwcoat.externalcoatingdate
                            obj['externalcoatingquality'] = rwcoat.externalcoatingquality
                            obj['supportMaterial'] = rwcoat.supportconfignotallowcoatingmaint
                            obj['InternalLining'] = rwcoat.internallining
                            obj['internallinertype'] = rwcoat.internallinertype
                            obj['internallinercondition'] = rwcoat.internallinercondition
                            obj['internalcladding'] = rwcoat.internalcladding
                            obj['claddingcorrosionrate'] = rwcoat.claddingcorrosionrate
                            obj['externalinsulation'] = rwcoat.externalinsulation
                            obj['externalinsulationtype'] = rwcoat.externalinsulationtype
                            obj['insulationcondition'] = rwcoat.insulationcondition
                            obj['insulationcontainschloride'] = rwcoat.insulationcontainschloride
                            if not componenttypeID in tank:
                                dataTank.append(obj)
    except Exception as e:
        print(e)
    return dataTank


def MainInpsectionPlan(request, siteID, name="", date=""):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    inspection = models.InspecPlan.objects.all()
    inspecCover = models.InspectionCoverage.objects.all()
    try:
        listInpsec = ListInpsectionPlan()
        listInpsecCoverage = []
        error = {}
        if '_select' in request.POST:
            for a in inspection:
                if (request.POST.get('%d' % a.id)):
                    return redirect('inspectionPlan', siteID=siteID, name=a.inspectionplanname,
                                    date=a.inspectionplandate)
        if '_delete' in request.POST:
            for a in inspection:
                if (request.POST.get('%d' % a.id)):
                    a.delete()
            return redirect('inspectionPlan', siteID=siteID)
        for a in inspection:
            if (a.inspectionplanname == name):
                listInpsecCoverage = ListInspectionCoverage(a.id)
        if '_creat' in request.POST:
            return redirect('createInspectionPlan', siteID=siteID)
        if '_add' in request.POST:
            if name == '':
                error['exist'] = "Please create/select an inspection plan before adding inspection coverage!"
            else:
                return redirect('addInspectionPlan', siteID=siteID, name=name, date=date, facilityID=0, equipID=0)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/inspection_plan/inspectionPlanNew.html',
                  {'page': 'inspectionPlan', 'siteID': siteID, 'count': count, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti,
                   'listInpsec': listInpsec, 'listInpsecCoverage': listInpsecCoverage, 'name': name, 'date': date,
                   'error': error})


def CreateInspectionPlan(request, siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    try:
        error = {}
        data = {}
        site = models.Sites.objects.filter(siteid=siteID)
        if request.method == 'POST':
            data['inspectionplanname'] = request.POST.get('InspectionPlan')
            data['inspectiondate'] = request.POST.get('InspectionDate')
            countIns = models.InspecPlan.objects.filter(inspectionplanname=data['inspectionplanname']).count()
            if countIns > 0:
                error['exist'] = "This Inspection Plan Name already exists!"
            else:
                ins = models.InspecPlan(inspectionplanname=data['inspectionplanname'],
                                        inspectionplandate=data['inspectiondate'])
                ins.save()
                return redirect('inspectionPlan', siteID=siteID, name=ins.inspectionplanname,
                                date=ins.inspectionplandate)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/inspection_plan/createInspectionPlan.html',
                  {'page': 'createInspectionPlan', 'site': site, 'error': error, 'data': data, 'siteID': siteID,
                   'count': count, 'info': request.session,
                   'noti': noti, 'countnoti': countnoti})


def AdddInssepctionPlan(request, siteID, facilityID, equipID, name, date):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()

    site = models.Sites.objects.all()
    facility = models.Facility.objects.filter(siteid_id=siteID)
    pros = models.RwAssessment.objects.all()

    siteT = models.Sites.objects.get(siteid=siteID)

    inspecplan = models.InspecPlan.objects.all()
    imtype = models.IMType.objects.all()
    imitem = models.IMItem.objects.all()
    try:
        siteAll = []
        typeInspec = []
        dataF = []
        listdata = {}
        equipName = ''
        dataSite = models.Sites.objects.all()
        for a in dataSite:
            siteobj = {}
            siteobj['ID'] = a.siteid
            siteobj['SiteName'] = a.sitename
            siteobj['Create'] = a.create
            siteAll.append(siteobj)
        for a in inspecplan:
            if (a.inspectionplanname == name):
                inspecCover = models.InspectionCoverage.objects.filter(planid_id=a.id)
                for b in inspecCover:
                    obj = {}
                    array = b.componentid_id
                    dataF.append(array)
        if request.POST.get('allSite'):
            allSite = 1
        else:
            allSite = 0
        if not facilityID:
            allSite = 1
            facName = "All"
            equip = models.EquipmentMaster.objects.all()
            equipName = "All"
        else:
            allSite = allSite
            fac = models.Facility.objects.get(facilityid=facilityID)
            facName = fac.facilityname
            equip = models.EquipmentMaster.objects.filter(facilityid_id=facilityID)
            if equipID:
                equipName = models.EquipmentMaster.objects.get(equipmentid=equipID)
            else:
                equipName = models.EquipmentMaster.objects.all()
        if allSite:
            data = ListNormalProposalFofInpsection(siteID=siteID, facilityID=0, equimentID=0)
            dataTank = ListTankProposalForInpsection(siteID=siteID, facilityID=0, equimentID=0)
        else:
            data = ListNormalProposalFofInpsection(siteID=siteID, facilityID=facilityID, equimentID=equipID)
            dataTank = ListTankProposalForInpsection(siteID=siteID, facilityID=facilityID, equimentID=equipID)
        if request.method == 'POST':
            listdata['inspectiontype'] = request.POST.get('InspectionType')
            listdata['visual'] = request.POST.get('Visual')
            listdata['nagnetic'] = request.POST.get('Magnetic')
            listdata['penetrant'] = request.POST.get('Penetrant')
            listdata['radiography'] = request.POST.get('Radiography')
            listdata['ultrasonic'] = request.POST.get('Ultrasonic')
            listdata['eddycurrent'] = request.POST.get('EddyCurrent')
            listdata['thermography'] = request.POST.get('Thermography')
            listdata['acousticemission'] = request.POST.get('AcousticEmission')
            listdata['metallurgical'] = request.POST.get('Metallurgical')
            listdata['monitoring'] = request.POST.get('Monitoring')
            if (listdata['inspectiontype'] == 'Intrusive'):
                inspectiontype = 1
            else:
                inspectiontype = 2
            listdata['cover1'] = request.POST.get('Cover1')
            listdata['cover2'] = request.POST.get('Cover2')
            listdata['cover3'] = request.POST.get('Cover3')
            listdata['cover4'] = request.POST.get('Cover4')
            listdata['cover5'] = request.POST.get('Cover5')
            listdata['cover6'] = request.POST.get('Cover6')
            listdata['cover7'] = request.POST.get('Cover7')
            listdata['cover8'] = request.POST.get('Cover8')
            listdata['cover9'] = request.POST.get('Cover9')
            listdata['cover10'] = request.POST.get('Cover10')
            obj1 = {}
            obj2 = {}
            obj3 = {}
            obj4 = {}
            obj5 = {}
            obj5 = {}
            obj6 = {}
            obj7 = {}
            obj8 = {}
            obj9 = {}
            obj10 = {}
            listCover = [listdata['cover1'], listdata['cover2'], listdata['cover3'], listdata['cover4'],
                         listdata['cover5'], listdata['cover6'], listdata['cover7'], listdata['cover8'],
                         listdata['cover9'], listdata['cover10']]
            if (listdata['visual'] == 'Endoscopy'):
                obj1['IMItemID'] = 1
                obj1['IMTypeID'] = 1
            elif (listdata['visual'] == 'Hydrotesting'):
                obj1['IMItemID'] = 1
                obj1['IMTypeID'] = 2
            elif (listdata['visual'] == 'Naked Eye'):
                obj1['IMItemID'] = 1
                obj1['IMTypeID'] = 3
            elif (listdata['visual'] == 'Video'):
                obj1['IMItemID'] = 1
                obj1['IMTypeID'] = 4
            elif (listdata['visual'] == 'Holiday'):
                obj1['IMItemID'] = 1
                obj1['IMTypeID'] = 37
            if (listdata['nagnetic'] == 'Magnetic Fluorescent Inspection'):
                obj2['IMItemID'] = 2
                obj2['IMTypeID'] = 5
            elif (listdata['nagnetic'] == 'Magnetic Flux Leakage'):
                obj2['IMItemID'] = 2
                obj2['IMTypeID'] = 6
            elif (listdata['nagnetic'] == 'Magnetic Particle Inspection'):
                obj2['IMItemID'] = 2
                obj2['IMTypeID'] = 7
            if (listdata['penetrant'] == 'Liquid Penetrant Inspection'):
                obj3['IMItemID'] = 3
                obj3['IMTypeID'] = 8
            elif (listdata['penetrant'] == 'Liquid Penetrant Inspection'):
                obj3['IMItemID'] = 3
                obj3['IMTypeID'] = 9
            if (listdata['radiography'] == 'Compton Scatter'):
                obj4['IMItemID'] = 4
                obj4['IMTypeID'] = 10
            elif (listdata['radiography'] == 'Gamma Radiography'):
                obj4['IMItemID'] = 4
                obj4['IMTypeID'] = 11
            elif (listdata['radiography'] == 'Real-time Radiography'):
                obj4['IMItemID'] = 4
                obj4['IMTypeID'] = 12
            elif (listdata['radiography'] == 'X-Radiography'):
                obj4['IMItemID'] = 4
                obj4['IMTypeID'] = 13
            if (listdata['ultrasonic'] == 'Angled Compression Wave'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 14
            elif (listdata['ultrasonic'] == 'Angled Shear Wave'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 15
            elif (listdata['ultrasonic'] == 'A-scan Thickness Survey'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 16
            elif (listdata['ultrasonic'] == 'B-scan'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 17
            elif (listdata['ultrasonic'] == 'Chime'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 18
            elif (listdata['ultrasonic'] == 'C-scan'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 19
            elif (listdata['ultrasonic'] == 'Digital Ultrasonic Thickness Gauge'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 20
            elif (listdata['ultrasonic'] == 'Lorus'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 21
            elif (listdata['ultrasonic'] == 'Surface Waves'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 22
            elif (listdata['ultrasonic'] == 'Teletest'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 23
            elif (listdata['ultrasonic'] == 'TOFD'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 24
            elif (listdata['ultrasonic'] == 'Advanced Ultrasonic Backscatter Technique'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 38
            elif (listdata['ultrasonic'] == 'Internal Rotational Inspection System'):
                obj5['IMItemID'] = 5
                obj5['IMTypeID'] = 39
            if (listdata['eddycurrent'] == 'ACFM'):
                obj6['IMItemID'] = 6
                obj6['IMTypeID'] = 25
            elif (listdata['eddycurrent'] == 'Low frequency'):
                obj6['IMItemID'] = 6
                obj6['IMTypeID'] = 26
            elif (listdata['eddycurrent'] == 'Pulsed'):
                obj6['IMItemID'] = 6
                obj6['IMTypeID'] = 27
            elif (listdata['eddycurrent'] == 'Remote field'):
                obj6['IMItemID'] = 6
                obj6['IMTypeID'] = 28
            elif (listdata['eddycurrent'] == 'Standard (flat coil)'):
                obj6['IMItemID'] = 6
                obj6['IMTypeID'] = 29
            if (listdata['thermography'] == 'Passive Thermography'):
                obj7['IMItemID'] = 7
                obj7['IMTypeID'] = 30
            elif (listdata['thermography'] == 'Transient Thermography'):
                obj7['IMItemID'] = 7
                obj7['IMTypeID'] = 31

            if (listdata['acousticemission'] == 'Crack Detection'):
                obj8['IMItemID'] = 8
                obj8['IMTypeID'] = 32
            elif (listdata['acousticemission'] == 'Leak Detection'):
                obj8['IMItemID'] = 8
                obj8['IMTypeID'] = 33
            if (listdata['metallurgical'] == 'Hardness Surveys'):
                obj9['IMItemID'] = 9
                obj9['IMTypeID'] = 34
            elif (listdata['metallurgical'] == 'Microstructure Replication'):
                obj9['IMItemID'] = 9
                obj9['IMTypeID'] = 35
            if (listdata['monitoring'] == 'On-line Monitoring'):
                obj10['IMItemID'] = 10
                obj10['IMTypeID'] = 36
            dataobj = [obj1, obj2, obj3, obj4, obj5, obj6, obj7, obj8, obj9, obj10]
            dataobjCopy = []
            i = 0
            for a in dataobj:
                if a:
                    a['Cover'] = listCover[i]
                    dataobjCopy.append(a)
                i = i + 1
        if '_select' in request.POST:
            for a in site:
                if (request.POST.get('%d' % a.siteid)):
                    return redirect('addInspectionPlan', siteID=a.siteid, name=name, date=date, facilityID=0, equipID=0)
        if '_selectFac' in request.POST:
            for a in facility:
                if (request.POST.get('%d' % a.facilityid)):
                    return redirect('addInspectionPlan', siteID=siteID, name=name, date=date, facilityID=a.facilityid,
                                    equipID=0)
        if '_selectEquip' in request.POST:
            for a in equip:
                if (request.POST.get('%d' % a.equipmentid)):
                    return redirect('addInspectionPlan', siteID=siteID, name=name, date=date, facilityID=facilityID,
                                    equipID=a.equipmentid)
        if '_cancel' in request.POST:
            return redirect('inspectionPlan', siteID=siteID, name=name, date=date)
        if '_ok' in request.POST:
            for b in inspecplan:
                inspectionCover = models.InspectionCoverage.objects.filter(planid_id=b.id)
                if (b.inspectionplanname == name):
                    if (inspectionCover.count() > 0):
                        for c in inspectionCover:
                            c.delete()
                            inspectionCoverDT = models.InspectionCoverageDetail.objects.filter(coverageid_id=c.id)
                            inspectDeTech = models.InspectionTechnique.objects.filter(coverageid_id=c.id)
                            for f in inspectDeTech:
                                f.delete()
                            for d in inspectionCoverDT:
                                d.delete()
            dataprosal = []
            for a in pros:
                if (request.POST.get('%d' % a.id)):
                    for b in inspecplan:
                        if (b.inspectionplanname == name):
                            inspecCover = models.InspectionCoverage(planid_id=b.id, equipmentid_id=a.equipmentid_id,
                                                                    componentid_id=a.componentid_id)
                            inspecCover.save()
                    dataprosal.append(a)
            inspectionCover = models.InspectionCoverage.objects.filter(planid_id=GetIdInpsecPlan(name))
            for d in inspectionCover:
                for f in dataobjCopy:
                    inspDetailTech = models.InspectionTechnique(coverageid_id=d.id, imitemid_id=f['IMItemID'],
                                                                imtypeid_id=f['IMTypeID'],
                                                                inspectiontype=inspectiontype, coverage=f['Cover'])
                    inspDetailTech.save()
                for u in dataprosal:
                    rwdama = models.RwDamageMechanism.objects.filter(id_dm_id=u.id)
                    for c in rwdama:
                        equip = models.RwAssessment.objects.get(id=u.id).equipmentid_id
                        comp = models.RwAssessment.objects.get(id=u.id).componentid_id
                        if ((d.equipmentid_id == equip) and (d.componentid_id == comp)):
                            dmitem = models.DMItems.objects.get(dmitemid=c.dmitemid_id)
                            inSpecCoverDT = models.InspectionCoverageDetail(coverageid_id=d.id,
                                                                            dmitemid_id=dmitem.dmitemid,
                                                                            inspectiondate=date)
                            inSpecCoverDT.save()
            return redirect('damageMechanism', planID=GetIdInpsecPlan(name), siteID=siteID)
    except Exception as e:
        print(e)
    return render(request, 'FacilityUI/inspection_plan/addInspectionPlan.html',
                  {'page': 'addInspectionPlan', 'siteID': siteID, 'count': count, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'allSite': allSite, 'siteAll': siteAll, 'siteT': siteT, 'allSite': allSite,
                   'facName': facName, 'facility': facility,
                   'equipName': equipName, 'equip': equip, 'data': data, 'dataTank': dataTank, 'dataF': dataF,
                   'imtype': imtype, 'imitem': imitem, 'name': name, 'date': date})


def DamamgeMechanism(request, planID, siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    inspecCover = models.InspectionCoverage.objects.filter(planid_id=planID)
    inspecPlan = models.InspecPlan.objects.get(id=planID)
    listDMItem = [8, 9, 61, 57, 67, 34, 32, 66, 69, 60, 72, 62, 70, 73]
    dataSumary = []
    try:
        if (inspecCover.count() == 1):
            inspecCover1 = models.InspectionCoverage.objects.get(planid_id=planID)
            inspecCoverDetail = models.InspectionCoverageDetail.objects.filter(coverageid_id=inspecCover1.id)
            inspecTech = models.InspectionTechnique.objects.filter(coverageid_id=inspecCover1.id)
            for b in inspecCoverDetail:
                listSub = ""
                obj = {}
                obj['InspectionDate'] = models.InspecPlan.objects.get(id=planID).inspectionplandate
                obj['CoverageID'] = inspecCover1.id
                obj['CoverageDetailID'] = b.id
                obj['DMITemID'] = b.dmitemid_id
                obj['ID'] = b.id
                obj['DMITemID'] = models.DMItems.objects.get(dmitemid=b.dmitemid_id).dmdescription
                obj['EquipmentName'] = models.EquipmentMaster.objects.get(
                    equipmentid=inspecCover1.equipmentid_id).equipmentnumber
                obj['ComponenttName'] = models.ComponentMaster.objects.get(
                    componentid=inspecCover1.componentid_id).componentnumber
                if b.dmitemid_id in listDMItem:
                    inspecDmRule = models.InspectionDMRule.objects.filter(dmitemid_id=b.dmitemid_id)
                    for f in inspecDmRule:
                        for c in inspecTech:
                            if ((f.imitemid_id == c.imitemid_id) and (f.imtypeid_id == c.imtypeid_id)):
                                obj1 = {}
                                if c.inspectiontype == 1:
                                    obj1['Type'] = "Intrusive"
                                else:
                                    obj1['Type'] = "Non-Intrusive"
                                obj1['Coverage'] = c.coverage
                                obj1['IMITemID'] = models.IMItem.objects.get(imitemid=c.imitemid_id).imdescription
                                obj1['IMTypeID'] = models.IMType.objects.get(imtypeid=c.imtypeid_id).imtypename
                                listSub = listSub + obj1['Type'] + "-" + obj1['IMITemID'] + "-" + obj1[
                                    'IMTypeID'] + "-" + str(obj1['Coverage']) + "%" + ";"
                obj['Summary'] = listSub
                dataSumary.append(obj)
        else:
            for a in inspecCover:
                inspecCoverDetail2 = models.InspectionCoverageDetail.objects.filter(coverageid_id=a.id)
                inspecTech = models.InspectionTechnique.objects.filter(coverageid_id=a.id)
                for b in inspecCoverDetail2:
                    listSub = ""
                    obj = {}
                    obj['InspectionDate'] = models.InspecPlan.objects.get(id=planID).inspectionplandate
                    obj['CoverageID'] = a.id
                    obj['CoverageDetailID'] = b.id
                    obj['DMITemID'] = b.dmitemid_id
                    obj['ID'] = b.id
                    obj['DMITemName'] = models.DMItems.objects.get(dmitemid=b.dmitemid_id).dmdescription
                    obj['EquipmentName'] = models.EquipmentMaster.objects.get(
                        equipmentid=a.equipmentid_id).equipmentnumber
                    obj['ComponenttName'] = models.ComponentMaster.objects.get(
                        componentid=a.componentid_id).componentnumber
                    if b.dmitemid_id in listDMItem:
                        inspecDmRule = models.InspectionDMRule.objects.filter(dmitemid_id=b.dmitemid_id)
                        for f in inspecDmRule:
                            for c in inspecTech:
                                if ((f.imitemid_id == c.imitemid_id) and (f.imtypeid_id == c.imtypeid_id)):
                                    obj1 = {}
                                    if c.inspectiontype == 1:
                                        obj1['Type'] = "Intrusive"
                                    else:
                                        obj1['Type'] = "Non-Intrusive"
                                    obj1['Coverage'] = c.coverage
                                    obj1['IMITemID'] = models.IMItem.objects.get(imitemid=c.imitemid_id).imdescription
                                    obj1['IMTypeID'] = models.IMType.objects.get(imtypeid=c.imtypeid_id).imtypename
                                    listSub = listSub + obj1['Type'] + "-" + obj1['IMITemID'] + "-" + obj1[
                                        'IMTypeID'] + "-" + str(obj1['Coverage']) + "%" + ";"
                    obj['Summary'] = listSub
                    dataSumary.append(obj)
        if '_ok' in request.POST:
            for a in dataSumary:
                if (request.POST.get('%d' % a['CoverageDetailID'])):
                    print(request.POST.get('EEF' + str(a['CoverageDetailID'])))
                    inspectionCoverDetail = models.InspectionCoverageDetail(id=a['ID'], coverageid_id=a['CoverageID'],
                                                                            dmitemid_id=a['DMITemID'],
                                                                            inspsummary=a['Summary'],
                                                                            effcode=request.POST.get(
                                                                                'EEF' + str(a['CoverageDetailID'])),
                                                                            inspectiondate=a['InspectionDate'],
                                                                            carriedoutdate=a['InspectionDate'],
                                                                            iscarriedout=0)
                    inspectionCoverDetail.save()
            return redirect('inspectionPlan', siteID=siteID, name=inspecPlan.inspectionplanname,
                            date=inspecPlan.inspectionplandate)
    except Exception as e:
        print(e)
        print("error in DamamgeMechanism")
    return render(request, 'FacilityUI/inspection_plan/damageMechanism.html',
                  {'page': 'DamageMechanism', 'siteID': siteID, 'count': count, 'noti': noti, 'countnoti': countnoti,
                   'dataSumary': dataSumary})


def GetIdInpsecPlan(name):
    inspecplan = models.InspecPlan.objects.all()
    for b in inspecplan:
        if (b.inspectionplanname == name):
            return b.id


################ Business UI Control ###################
def ListFacilities(request, siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    try:
        risk = []
        error={}
        result = {}
        data = models.Facility.objects.filter(siteid=siteID)
        if '_search' in request.POST and request.POST.get('searchFacility')!="":
            search = request.POST.get('searchFacility')
            for a in data:
                print(a.facilityname)
                print(search)
                risTarget = models.FacilityRiskTarget.objects.get(facilityid=a.facilityid)
                if(a.facilityname == search or str(a.managementfactor)==search or str(risTarget.risktarget_fc)==search):
                    dataF = {}
                    dataF['ID'] = a.facilityid
                    dataF['FacilitiName'] = a.facilityname
                    dataF['CreatedTime'] = a.create
                    dataF['ManagementFactor'] = a.managementfactor
                    dataF['RiskTarget'] = risTarget.risktarget_fc
                    risk.append(dataF)
            i=0
            for b in risk:
                i=i+1
            print(i)
            if i:
                result['data'] = str(i) + " kết quả với từ khóa " + search
            else:
                print("go error")
                error['exist'] = "Không thể tìm thấy " + "'" + search + "'" + " trong bất kỳ thư mục nào"
        else:
            for a in data:
                dataF = {}
                risTarget = models.FacilityRiskTarget.objects.get(facilityid=a.facilityid)
                dataF['ID'] = a.facilityid
                dataF['FacilitiName'] = a.facilityname
                dataF['CreatedTime'] = a.create
                dataF['ManagementFactor'] = a.managementfactor
                dataF['RiskTarget'] = risTarget.risktarget_fc
                risk.append(dataF)
        pagiFaci = Paginator(risk, 25)
        pageFaci = request.GET.get('page', 1)
        try:
            users = pagiFaci.page(pageFaci)
        except PageNotAnInteger:
            users = pagiFaci.page(1)
        except EmptyPage:
            users = pageFaci.page(pagiFaci.num_pages)
        if '_edit' in request.POST:
            for a in data:
                if (request.POST.get('%d' % a.facilityid)):
                    return redirect('facilitiesEdit', a.facilityid)
        try:
            if '_delete' in request.POST:
                for a in data:
                    if (request.POST.get('%d' % a.facilityid)):
                        facilityname = models.Facility.objects.get(facilityid=a.facilityid).facilityname
                        user = models.ZUser.objects.get(kind='manager').id
                        noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                                    content=' đã xóa nhà máy ', object=facilityname,
                                                    link=siteID,
                                                    time=datetime.now(), state=0)
                        noti.save()
                        a.delete()
                return redirect('facilitiesDisplay', siteID)
        except Exception as e:
            print(e)
            raise Http404
        if '_new' in request.POST:
            return redirect('facilitiesNew', siteID=siteID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/facility/facilityListDisplay.html',
                  {'page': 'listFacility', 'obj': users,'siteID': siteID,'error':error,'result':result ,'count': count, 'info': request.session,
                   'noti': noti, 'countnoti': countnoti})


def NewFacilities(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        data = {}
        site = models.Sites.objects.filter(siteid=siteID)
        if '_helpfms' in request.POST:
            data['facilityname'] = request.POST.get('FacilityName')
            data['manageFactor'] = request.POST.get('ManagementSystemFactor')
            data['targetFC'] = request.POST.get('Financial')
            data['targetAC'] = request.POST.get('Area')
            fa = models.Facility(facilityname=data['facilityname'], managementfactor=data['manageFactor'],
                                 siteid_id=siteID)
            fa.save()
            faTarget = models.FacilityRiskTarget(facilityid_id=fa.facilityid, risktarget_ac=data['targetAC'],
                                                 risktarget_fc=data['targetFC'])
            faTarget.save()
            faci=models.Facility.objects.filter(siteid_id=siteID)
            faciid=0
            for i in faci:
                if i.facilityname==data['facilityname']:
                    faciid=i.facilityid
            return redirect('managmentsystems', facilityID=faciid)
        if request.method == 'POST':
            data['facilityname'] = request.POST.get('FacilityName')
            data['manageFactor'] = request.POST.get('ManagementSystemFactor')
            data['targetFC'] = request.POST.get('Financial')
            data['targetAC'] = request.POST.get('Area')
            countFaci = models.Facility.objects.filter(facilityname=data['facilityname']).count()

            if countFaci > 0:
                error['exist'] = "This facility already exists!"
            else:
                fa = models.Facility(facilityname=data['facilityname'], managementfactor=data['manageFactor'],
                                     siteid_id=siteID)
                fa.save()
                faTarget = models.FacilityRiskTarget(facilityid_id=fa.facilityid, risktarget_ac=data['targetAC'],
                                                     risktarget_fc=data['targetFC'])
                faTarget.save()
                user = models.ZUser.objects.get(kind='manager').id
                noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                            content=' đã thêm nhà máy ', object=data['facilityname'],
                                            link=siteID,
                                            time=datetime.now(), state=0)
                noti.save()
                return redirect('facilitiesDisplay', siteID=siteID)
    except:
        raise Http404
    return render(request, 'FacilityUI/facility/facilityNew.html',
                  {'page': 'newFacility', 'site': site, 'error': error, 'data': data, 'siteID': siteID,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def EditFacilities(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        dataNew = {}
        dataOld = models.Facility.objects.get(facilityid=facilityID)
        dataRisk = models.FacilityRiskTarget.objects.get(facilityid=facilityID)
        site = models.Sites.objects.get(siteid=dataOld.siteid_id)
        dataNew['facilityname'] = dataOld.facilityname
        dataNew['manageFactor'] = dataOld.managementfactor
        dataNew['targetFC'] = dataRisk.risktarget_fc
        dataNew['targetAC'] = dataRisk.risktarget_ac
        dataNew['sitename'] = site.sitename
        if '_helpfms' in request.POST:
            return redirect('managmentsystems', facilityID=facilityID)
        if request.method == 'POST':
            dataNew['facilityname'] = request.POST.get('FacilityName')
            dataNew['manageFactor'] = request.POST.get('ManagementSystemFactor')
            dataNew['targetFC'] = request.POST.get('Financial')
            dataNew['targetAC'] = request.POST.get('Area')
            countFaci = models.Facility.objects.filter(facilityname=dataNew['facilityname']).count()
            if dataNew['facilityname'] != dataOld.facilityname and countFaci > 0:
                error['exist'] = "This facility already exists!"
            else:
                dataOld.facilityname = dataNew['facilityname']
                dataOld.managementfactor = dataNew['manageFactor']
                dataOld.save()

                dataRisk.risktarget_fc = dataNew['targetFC']
                dataRisk.risktarget_ac = dataNew['targetAC']
                dataRisk.save()

                return redirect('facilitiesDisplay', siteID=dataOld.siteid_id)

    except:
        raise Http404
    return render(request, 'FacilityUI/facility/facilityEdit.html',
                  {'page': 'editFacility', 'dataNew': dataNew, 'error': error, 'siteID': dataOld.siteid_id,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def ListDesignCode(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        faci = models.Facility.objects.get(facilityid=facilityID)
        data = models.DesignCode.objects.filter(siteid=faci.siteid_id)
        pagiDes = Paginator(data, 25)
        pageDes = request.GET.get('page', 1)
        try:
            obj = pagiDes.page(pageDes)
        except PageNotAnInteger:
            obj = pagiDes.page(1)
        except EmptyPage:
            obj = pageDes.page(pagiDes.num_pages)
        if '_edit' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.designcodeid):
                    return redirect('designcodeEdit', designcodeID=a.designcodeid)
        if '_delete' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.designcodeid):
                    a.delete()
            return redirect('designcodeDisplay', siteID=siteID)
        if '_new' in request.POST:
            return redirect('designcodeNew', siteID=siteID)
    except:
        raise Http404
    return render(request, 'FacilityUI/design_code/designcodeListDisplay.html',
                  {'page': 'listDesign', 'obj': obj, 'siteID': faci.siteid_id,'facilityID':facilityID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def CorrisionRate(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()

    try:
        list = []
        dataF = {}
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 9 or component.componenttypeid_id == 13:
            isShell = 1
        else:
            isShell = 0
        componentID = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        dataF = models.CorrosionRateTank.objects.filter(id_id=proposalID)
        for a in dataF:
            list.append(a)
        error = {}
        data = {}
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        if request.method == 'POST':
            data['corrision'] = request.POST.get('CorrisionID')
            data['soilsidecorrosionrate'] = request.POST.get('SoilSideCorrosionRate')
            data['productsidecorrosionrate'] = request.POST.get('ProductSideCorrosionRate')
            data['potentialporrosion'] = request.POST.get('PotentialCorrosion')
            data['tankpadmaterial'] = request.POST.get('TankPadMaterial')
            data['tankdrainagetype'] = request.POST.get('TankDrainageType')
            data['cathodicprotectiontype'] = request.POST.get('CathodicProtectionType')
            data['tankbottomtype'] = request.POST.get('TankBottomType')
            data['soilsidetemperature'] = request.POST.get('SoilSideTemperature')
            data['productcondition'] = request.POST.get('ProductCondition')
            data['productsidetemp'] = request.POST.get('ProductSideTemp')
            data['steamcoil'] = request.POST.get('SteamCoil')
            data['waterdrawoff'] = request.POST.get('WaterDrawOff')
            data['productsidebottom'] = request.POST.get('ProductSideBottom')
            data['modifiedsoilsidecorrosionrate'] = request.POST.get('ModifiedSoilSideCorrosionRate')
            data['modifiedproductsidecorrosionrate'] = request.POST.get('ModifiedProductSideCorrosionRate')
            data['finalestimatedcorrosionrate'] = request.POST.get('FinalEstimatedCorrosionRate')
            countCorri = models.CorrosionRateTank.objects.filter(corrosionid=data['corrision']).count()
            if countCorri > 0:
                error['exist'] = "This corrision already exists!"

            else:
                cor = models.CorrosionRateTank(id_id=rwAss.id,
                                               corrosionid=data['corrision'],
                                               soilsidecorrosionrate=data['soilsidecorrosionrate'],
                                               productsidecorrosionrate=data['productsidecorrosionrate'],
                                               potentialcorrosion=data['potentialporrosion'],
                                               tankpadmaterial=data['tankpadmaterial'],
                                               tankdrainagetype=data['tankdrainagetype'],
                                               cathodicprotectiontype=data['cathodicprotectiontype'],
                                               tankbottomtype=data['tankbottomtype'],
                                               soilsidetemperature=data['soilsidetemperature'],
                                               productcondition=data['productcondition'],
                                               productsidetemp=data['productsidetemp'],
                                               steamcoil=data['steamcoil'], waterdrawoff=data['waterdrawoff'],
                                               productsidebottom=data['productsidebottom'])
                cor.save()
                try:
                    ReCalculate.ReCalculate(proposalID)
                except Exception as e:
                    print(e)
                    raise Http404
                return redirect('corrision', proposalID=proposalID)
        if '_delete' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.corrosionid):
                    a.delete()
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/risk_summary/proposalCorrisionRate.html',
                  {'page': 'corrsionRate', 'proposalID': proposalID, 'componentID': rwAss.componentid_id,
                   'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count, 'list': list, 'dataF': dataF, 'isTank': isBottom,
                   'isShell': isShell})


def CaculateCorrision(request, proposalID):
    return render(request, 'FacilityUI/risk_summary/CaculateCorrision.html',
                  {'page': 'caculateCorri', 'proposalID': proposalID})


def NewDesignCode(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        data = {}
        if request.method == 'POST':
            data['designcode'] = request.POST.get('design_code_name')
            data['designcodeapp'] = request.POST.get('design_code_app')
            count = models.DesignCode.objects.filter(designcode=data['designcode']).count()
            if count > 0:
                error['exist'] = "This design code already exist!"
            else:
                ds = models.DesignCode(designcode=data['designcode'], designcodeapp=data['designcodeapp'],
                                       siteid_id=siteID)
                ds.save()
                return redirect('designcodeDisplay', siteID=siteID)
    except:
        raise Http404
    return render(request, 'FacilityUI/design_code/designcodeNew.html',
                  {'page': 'newDesign', 'data': data, 'error': error, 'siteID': siteID, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def EditDesignCode(request, designcodeID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        dataNew = {}
        dataOld = models.DesignCode.objects.get(designcodeid=designcodeID)
        dataNew['designcode'] = dataOld.designcode
        dataNew['designcodeapp'] = dataOld.designcodeapp
        if request.method == 'POST':
            dataNew['designcode'] = request.POST.get('design_code_name')
            dataNew['designcodeapp'] = request.POST.get('design_code_app')
            count = models.DesignCode.objects.filter(designcode=dataNew['designcodeapp']).count()
            if dataNew['designcode'] != dataOld.designcode and count > 0:
                error['exist'] = "This design code already exist!"
            else:
                dataOld.designcode = dataNew['designcode']
                dataOld.designcodeapp = dataNew['designcodeapp']
                dataOld.save()
                return redirect('designcodeDisplay', siteID=dataOld.siteid_id)
    except:
        raise Http404
    return render(request, 'FacilityUI/design_code/designcodeEdit.html',
                  {'page': 'editDesign', 'data': dataNew, 'error': error, 'siteID': dataOld.siteid_id, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def ListManufacture(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        faci = models.Facility.objects.get(facilityid=facilityID)
        data = models.Manufacturer.objects.filter(siteid=faci.siteid_id)
        pagiManu = Paginator(data, 25)
        pageManu = request.GET.get('page', 1)
        try:
            obj = pagiManu.page(pageManu)
        except PageNotAnInteger:
            obj = pagiManu.page(1)
        except EmptyPage:
            obj = pageManu.page(pagiManu.num_pages)
        if '_edit' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.manufacturerid):
                    return redirect('manufactureEdit', manufactureID=a.manufacturerid)
        if '_delete' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.manufacturerid):
                    a.delete()
            return redirect('manufactureDisplay', siteID=siteID)
        if '_new' in request.POST:
            return redirect('manufactureNew', siteID=siteID)
    except:
        raise Http404
    return render(request, 'FacilityUI/manufacture/manufactureListDisplay.html',
                  {'page': 'listManu', 'obj': obj, 'siteID': faci.siteid_id,'facilityID':facilityID, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def NewManufacture(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        data = {}
        if request.method == 'POST':
            data['manufacture'] = request.POST.get('manufacture')
            count = models.Manufacturer.objects.filter(manufacturername=data['manufacture']).count()
            if count > 0:
                error['exist'] = 'This manufacture already exist!'
            else:
                manu = models.Manufacturer(siteid_id=siteID, manufacturername=data['manufacture'])
                manu.save()
                return redirect('manufactureDisplay', siteID=siteID)
    except:
        raise Http404
    return render(request, 'FacilityUI/manufacture/manufactureNew.html',
                  {'page': 'newManu', 'data': data, 'error': error, 'siteID': siteID, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def EditManufacture(request, manufactureID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        dataNew = {}
        dataOld = models.Manufacturer.objects.get(manufacturerid=manufactureID)
        dataNew['manufacture'] = dataOld.manufacturername
        if request.method == 'POST':
            dataNew['manufacture'] = request.POST.get('manufacture')
            count = models.Manufacturer.objects.filter(manufacturername=dataNew['manufacture']).count()
            if dataNew['manufacture'] != dataOld.manufacturername and count > 0:
                error['exist'] = 'This manufacturer already exist!'
            else:
                dataOld.manufacturername = dataNew['manufacture']
                dataOld.save()
                return redirect('manufactureDisplay', siteID=dataOld.siteid_id)
    except:
        raise Http404
    return render(request, 'FacilityUI/manufacture/manufactureEdit.html',
                  {'page': 'editManu', 'data': dataNew, 'error': error, 'siteID': dataOld.siteid_id, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def ListEquipment(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        faci = models.Facility.objects.get(facilityid=facilityID)
        data = models.EquipmentMaster.objects.filter(facilityid=facilityID)
        risk = []
        error = {}
        result = {}
        if '_search' in request.POST and request.POST.get('searchEquipment') != "":
            search = request.POST.get('searchEquipment')
            for a in data:
                equiptype = models.EquipmentType.objects.get(equipmenttypeid=a.equipmenttypeid_id)
                if (a.equipmentname == search or a.equipmentnumber==search or equiptype.equipmenttypename==search):
                    dataF = {}
                    dataF['ID'] = a.equipmentid
                    dataF['EquipmentName'] = a.equipmentname
                    dataF['Created'] = a.create
                    dataF['EquipmentType'] = equiptype.equipmenttypename
                    dataF['EquipmentNumber'] = a.equipmentnumber
                    risk.append(dataF)
            i = 0
            for b in risk:
                i = i + 1
            print(i)
            if i:
                result['data'] = str(i) + " kết quả với từ khóa " + search
            else:
                print("go error")
                error['exist'] = "Không thể tìm thấy " + "'" + search + "'" + " trong bất kỳ thư mục nào"
        else:
            for a in data:
                equiptype = models.EquipmentType.objects.get(equipmenttypeid=a.equipmenttypeid_id)
                dataF = {}
                dataF['ID'] = a.equipmentid
                dataF['EquipmentName'] = a.equipmentname
                dataF['Created'] = a.create
                dataF['EquipmentType'] = equiptype.equipmenttypename
                dataF['EquipmentNumber'] = a.equipmentnumber
                risk.append(dataF)
        pagiEquip = Paginator(risk, 25)
        pageEquip = request.GET.get('page', 1)
        try:
            obj = pagiEquip.page(pageEquip)
        except PageNotAnInteger:
            obj = pagiEquip.page(1)
        except EmptyPage:
            obj = pageEquip.page(pagiEquip.num_pages)
        if '_edit' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.equipmentid):
                    return redirect('equipmentEdit', equipmentID=a.equipmentid)
        if '_delete' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.equipmentid):
                    user = models.ZUser.objects.get(kind='manager').id
                    equipmentname = models.EquipmentMaster.objects.get(equipmentid=a.equipmentid).equipmentname
                    noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                                content=' đã xóa thiết bị ', object=equipmentname,
                                                link=facilityID,
                                                time=datetime.now(), state=0)
                    noti.save()
                    a.delete()
            return redirect('equipmentDisplay', facilityID=facilityID)
        if '_new' in request.POST:
            return redirect('equipmentNew', facilityID=facilityID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/equipment/equipmentListDisplay.html',
                  {'page': 'listEquip', 'obj': obj, 'facilityID': facilityID, 'siteID': faci.siteid_id, 'faci': faci,
                   'info': request.session,'error':error,'result':result ,'noti': noti, 'countnoti': countnoti, 'count': count})


def NewEquipment(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        data = {}
        error = {}
        faci = models.Facility.objects.get(facilityid=facilityID)
        manufacture = models.Manufacturer.objects.filter(siteid=faci.siteid_id)
        designcode = models.DesignCode.objects.filter(siteid=faci.siteid_id)
        equipmenttype = models.EquipmentType.objects.all()
        if request.method == 'POST':
            data['equipmentnumber'] = request.POST.get('equipmentNumber')
            data['equipmentname'] = request.POST.get('equipmentName')
            data['equipmenttype'] = request.POST.get('equipmentType')
            data['designcode'] = request.POST.get('designCode')
            data['manufacture'] = request.POST.get('manufacture')
            data['commissiondate'] = request.POST.get('CommissionDate')
            data['pdf'] = request.POST.get('PDFNo')
            data['processdescrip'] = request.POST.get('processDescription')
            data['description'] = request.POST.get('decription')
            count = models.EquipmentMaster.objects.filter(equipmentnumber=data['equipmentnumber']).count()
            if count > 0:
                error['exist'] = 'This equipment already exist!'
            else:
                eq = models.EquipmentMaster(equipmentnumber=data['equipmentnumber'],
                                            equipmentname=data['equipmentname'],
                                            equipmenttypeid_id=models.EquipmentType.objects.get(
                                                equipmenttypename=data['equipmenttype']).equipmenttypeid,
                                            designcodeid_id=models.DesignCode.objects.get(
                                                designcode=data['designcode']).designcodeid, siteid_id=faci.siteid_id,
                                            facilityid_id=facilityID,
                                            manufacturerid_id=models.Manufacturer.objects.get(
                                                manufacturername=data['manufacture']).manufacturerid,
                                            commissiondate=data['commissiondate'], pfdno=data['pdf'],
                                            processdescription=data['processdescrip'],
                                            equipmentdesc=data['description'])
                eq.save()
                user = models.ZUser.objects.get(kind='manager').id
                noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                            content=' đã thêm thiết bị ', object=data['equipmentname'],
                                            link=facilityID,
                                            time=datetime.now(), state=0)
                noti.save()
                return redirect('equipmentDisplay', facilityID=facilityID)
    except:
        raise Http404
    return render(request, 'FacilityUI/equipment/equipmentNew.html',
                  {'page': 'newEquip', 'data': data, 'equipmenttype': equipmenttype, 'designcode': designcode,
                   'manufacture': manufacture, 'facilityID': facilityID, 'siteID': faci.siteid_id,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def EditEquipment(request, equipmentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        error = {}
        dataNew = {}
        dataOld = models.EquipmentMaster.objects.get(equipmentid=equipmentID)
        manufacture = models.Manufacturer.objects.filter(siteid=dataOld.siteid_id)
        designcode = models.DesignCode.objects.filter(siteid=dataOld.siteid_id)
        dataNew['equipmentnumber'] = dataOld.equipmentnumber
        dataNew['equipmentname'] = dataOld.equipmentname
        dataNew['equipmenttype'] = models.EquipmentType.objects.get(
            equipmenttypeid=dataOld.equipmenttypeid_id).equipmenttypename
        dataNew['designcode'] = models.DesignCode.objects.get(designcodeid=dataOld.designcodeid_id).designcode
        dataNew['manufacture'] = models.Manufacturer.objects.get(
            manufacturerid=dataOld.manufacturerid_id).manufacturername
        dataNew['commissiondate'] = dataOld.commissiondate.date().strftime('%Y-%m-%d')
        dataNew['pdf'] = dataOld.pfdno
        dataNew['processdescrip'] = dataOld.processdescription
        dataNew['description'] = dataOld.equipmentdesc
        if request.method == 'POST':
            dataNew['equipmentnumber'] = request.POST.get('equipmentNumber')
            dataNew['equipmentname'] = request.POST.get('equipmentName')
            dataNew['designcode'] = request.POST.get('designCode')
            dataNew['manufacture'] = request.POST.get('manufacture')
            dataNew['commissiondate'] = request.POST.get('CommissionDate')
            dataNew['pdf'] = request.POST.get('PDFNo')
            dataNew['processdescrip'] = request.POST.get('processDescription')
            dataNew['description'] = request.POST.get('decription')
            count = models.EquipmentMaster.objects.filter(equipmentnumber=dataNew['equipmentnumber']).count()
            if dataNew['equipmentnumber'] != dataOld.equipmentnumber and count > 0:
                error['exist'] = 'This equipment already exist!'
            else:
                dataOld.equipmentnumber = dataNew['equipmentnumber']
                dataOld.equipmentname = dataNew['equipmentname']
                dataOld.designcodeid_id = models.DesignCode.objects.get(designcode=dataNew['designcode']).designcodeid
                dataOld.manufacturerid_id = models.Manufacturer.objects.get(
                    manufacturername=dataNew['manufacture']).manufacturerid
                dataOld.commissiondate = dataNew['commissiondate']
                dataOld.pfdno = dataNew['pdf']
                dataOld.processdescription = dataNew['processdescrip']
                dataOld.equipmentdesc = dataNew['description']
                dataOld.save()
                return redirect('equipmentDisplay', facilityID=dataOld.facilityid_id)
    except:
        raise Http404
    return render(request, 'FacilityUI/equipment/equipmentEdit.html',
                  {'page': 'editEquip', 'data': dataNew, 'error': error, 'designcode': designcode,
                   'manufacture': manufacture, 'facilityID': dataOld.facilityid_id, 'siteID': dataOld.siteid_id,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def ListComponent(request, equipmentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        eq = models.EquipmentMaster.objects.get(equipmentid=equipmentID)
        faci = models.Facility.objects.get(facilityid=eq.facilityid_id)
        data = models.ComponentMaster.objects.filter(equipmentid=equipmentID)
        risk = []
        error = {}
        result = {}
        if '_search' in request.POST and request.POST.get('searchComponent') != "":
            search = request.POST.get('searchComponent')
            for a in data:
                componentType = models.ComponentType.objects.get(componenttypeid=a.componenttypeid_id)
                if (a.componentnumber == search or a.componentname==search or componentType.componenttypename==search):
                    dataF = {}
                    dataF['ID'] = a.componentid
                    dataF['ComponentNumber'] = a.componentnumber
                    dataF['ComponentName'] = a.componentname
                    dataF['ComponentType'] = componentType.componenttypename
                    dataF['Created'] = a.create
                    risk.append(dataF)
            i = 0
            for b in risk:
                i = i + 1
            print(i)
            if i:
                result['data'] = str(i) + " kết quả trả về với từ khóa " + search
            else:
                print("go error")
                error['exist'] = "Không thể tìm thấy " + "'" + search + "'" + " trong bất kỳ thư mục nào"
        else:
            for a in data:
                dataF = {}
                componentType = models.ComponentType.objects.get(componenttypeid=a.componenttypeid_id)
                dataF['ID'] = a.componentid
                dataF['ComponentNumber'] = a.componentnumber
                dataF['ComponentName'] = a.componentname
                dataF['ComponentType'] = componentType.componenttypename
                dataF['Created'] = a.create
                risk.append(dataF)
        pagiComp = Paginator(risk, 25)
        pageComp = request.GET.get('page', 1)
        try:
            obj = pagiComp.page(pageComp)
        except PageNotAnInteger:
            obj = pagiComp.page(1)
        except EmptyPage:
            obj = pageComp.page(pagiComp.num_pages)
        if '_edit' in request.POST:
            for a in data:
                if request.POST.get('%a' % a.componentid):
                    return redirect('componentEdit', componentID=a.componentid)
        if '_delete' in request.POST:
            for a in data:
                if request.POST.get('%d' % a.componentid):
                    componentname = models.ComponentMaster.objects.get(componentid=a.componentid).componentname
                    user = models.ZUser.objects.get(kind='manager').id
                    noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                                content=' đã xóa thành phần ', object=componentname,
                                                link=equipmentID,
                                                time=datetime.now(), state=0)
                    noti.save()
                    a.delete()
            return redirect('componentDisplay', equipmentID=equipmentID)
        if '_new' in request.POST:
            return redirect('componentNew', equipmentID=equipmentID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/component/componentListDisplay.html',
                  {'page': 'listComp', 'obj': obj, 'equipmentID': equipmentID,'error':error ,'result':result,'facilityID': eq.facilityid_id, 'eq': eq,
                   'faci': faci, 'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def NewComponent(request, equipmentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        eq = models.EquipmentMaster.objects.get(equipmentid=equipmentID)
        data = {}
        error = {}
        componentType = models.ComponentType.objects.all()
        apicomponentType = models.ApiComponentType.objects.all()
        prdType = models.PRDType.objects.all()
        # tankapi = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 36, 38, 39]
        tankapi = [36, 38, 39]
        other = []
        for a in apicomponentType:
            if a.apicomponenttypeid not in tankapi:
                other.append(a)
        if request.method == 'POST':
            data['componentNumber'] = request.POST.get('componentNumber')
            data['componenttype'] = request.POST.get('componentType')
            data['apicomponenttype'] = request.POST.get('apiComponentType')
            data['componentname'] = request.POST.get('componentName')
            data['prdtype'] = request.POST.get('prdType')
            if request.POST.get('comRisk'):
                data['link'] = 1
            else:
                data['link'] = 0
            data['description'] = request.POST.get('description')
            count = models.ComponentMaster.objects.filter(componentnumber=data['componentNumber']).count()
            if count > 0:
                error['exist'] = 'This component already exist!'
            else:
                comp = models.ComponentMaster(componentnumber=data['componentNumber'], equipmentid_id=equipmentID,
                                              componenttypeid_id=models.ComponentType.objects.get(
                                                  componenttypename=data['componenttype']).componenttypeid,
                                              componentname=data['componentname'], componentdesc=data['description'],
                                              isequipmentlinked=data['link'],
                                              apicomponenttypeid=models.ApiComponentType.objects.get(
                                                  apicomponenttypename=data['apicomponenttype']).apicomponenttypeid)
                comp.save()
                user = models.ZUser.objects.get(kind='manager').id
                noti = models.ZNotification(id_user=user, subject=request.session['name'],
                                            content=' đã thêm thành phần ', object=data['componentNumber'],
                                            link=equipmentID,
                                            time=datetime.now(), state=0)
                noti.save()
                return redirect('componentDisplay', equipmentID=equipmentID)
    except:
        raise Http404
    return render(request, 'FacilityUI/component/componentNew.html',
                  {'page': 'newComp', 'error': error, 'componenttype': componentType, 'api': apicomponentType,
                   'other': other, 'data': data, 'equipmentID': equipmentID, 'facilityID': eq.facilityid_id,
                   'noti': noti, 'countnoti': countnoti, 'count': count, 'prdtype': prdType})


def EditComponent(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        dataNew = {}
        error = {}
        dataOld = models.ComponentMaster.objects.get(componentid=componentID)
        dataNew['componentnumber'] = dataOld.componentnumber
        dataNew['componentname'] = dataOld.componentname
        dataNew['componenttype'] = models.ComponentType.objects.get(
            componenttypeid=dataOld.componenttypeid_id).componenttypename
        dataNew['apicomponenttype'] = models.ApiComponentType.objects.get(
            apicomponenttypeid=dataOld.apicomponenttypeid).apicomponenttypename
        dataNew['link'] = dataOld.isequipmentlinked
        dataNew['description'] = dataOld.componentdesc
        if request.method == 'POST':
            dataNew['componentnumber'] = request.POST.get('componentNumer')
            dataNew['componentname'] = request.POST.get('componentName')
            if request.POST.get('comRisk'):
                dataNew['link'] = 1
            else:
                dataNew['link'] = 0
            dataNew['description'] = request.POST.get('decription')
            count = models.ComponentMaster.objects.filter(componentnumber=dataNew['componentnumber']).count()
            if count > 0 and dataNew['componentnumber'] != dataOld.componentnumber:
                error['exist'] = 'This component already exist!'
            else:
                dataOld.componentnumber = dataNew['componentnumber']
                dataOld.componentname = dataNew['componentname']
                dataOld.isequipmentlinked = dataNew['link']
                dataOld.componentdesc = dataNew['description']
                dataOld.save()
                return redirect('componentDisplay', equipmentID=dataOld.equipmentid_id)
    except:
        raise Http404
    return render(request, 'FacilityUI/component/componentEdit.html',
                  {'page': 'editComp', 'data': dataNew, 'error': error, 'equipmentID': dataOld.equipmentid_id,
                   'noti': noti, 'countnoti': countnoti, 'count': count,
                   'facilityID': models.EquipmentMaster.objects.get(equipmentid=dataOld.equipmentid_id).facilityid_id})


def ListProposal(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwass = models.RwAssessment.objects.filter(componentid=componentID)
        data = []
        error={}
        result={}
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        api = models.ApiComponentType.objects.get(apicomponenttypeid=comp.apicomponenttypeid)
        equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        tank = [8, 12, 14, 15]
        # tank = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 36, 38, 39]
        if '_search' in request.POST and request.POST.get('searchProposal') != "":
            search = request.POST.get('searchProposal')
            for a in rwass:
                df = models.RwFullPof.objects.filter(id=a.id)
                fc = models.RwFullFcof.objects.filter(id=a.id)
                dm = models.RwDamageMechanism.objects.filter(id_dm=a.id)
                if (a.proposalname == search):
                    obj1 = {}
                    obj1['id'] = a.id
                    obj1['name'] = a.proposalname
                    obj1['lastinsp'] = a.assessmentdate.strftime('%Y-%m-%d')
                    if df.count() != 0:
                        obj1['df'] = round(df[0].totaldfap1, 2)
                        obj1['gff'] = df[0].gfftotal
                        obj1['fms'] = df[0].fms
                    else:
                        obj1['df'] = 0
                        obj1['gff'] = 0
                        obj1['fms'] = 0
                    if fc.count() != 0:
                        obj1['fc'] = round(fc[0].fcofvalue, 2)
                    else:
                        obj1['fc'] = 0
                    if dm.count() != 0:
                        obj1['duedate'] = dm[0].inspduedate.date().strftime('%Y-%m-%d')
                        obj1['lastinsp'] = dm[0].lastinspdate.date().strftime('%Y-%m-%d')
                    else:
                        # obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=15)).strftime('%Y-%m-%d')
                        obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=16)).strftime(
                            '%Y-%m-%d')  # cuong sua
                        obj1['lastinsp'] = equip.commissiondate.date().strftime('%Y-%m-%d')  # cuong them vao
                    obj1['risk'] = round(obj1['df'] * obj1['gff'] * obj1['fms'] * obj1['fc'], 2)
                    data.append(obj1)
            i = 0
            for b in data:
                i = i + 1
            print(i)
            if i:
                result['data'] = str(i) + " kết quả trả về với từ khóa " + search
            else:
                print("go error")
                error['exist'] = "Không thể tìm thấy" + "'" + search + "'" + " trong bất kỳ thư mục nào"
        else:
            for a in rwass:
                df = models.RwFullPof.objects.filter(id=a.id)
                fc = models.RwFullFcof.objects.filter(id=a.id)
                dm = models.RwDamageMechanism.objects.filter(id_dm=a.id)
                obj1 = {}
                obj1['id'] = a.id
                obj1['name'] = a.proposalname
                obj1['lastinsp'] = a.assessmentdate.strftime('%Y-%m-%d')
                if df.count() != 0:
                    obj1['df'] = round(df[0].totaldfap1, 2)
                    obj1['gff'] = df[0].gfftotal
                    obj1['fms'] = df[0].fms
                else:
                    obj1['df'] = 0
                    obj1['gff'] = 0
                    obj1['fms'] = 0
                if fc.count() != 0:
                    obj1['fc'] = round(fc[0].fcofvalue, 2)
                else:
                    obj1['fc'] = 0
                if dm.count() != 0:
                    obj1['duedate'] = dm[0].inspduedate.date().strftime('%Y-%m-%d')
                    obj1['lastinsp'] = dm[0].lastinspdate.date().strftime('%Y-%m-%d')
                else:
                    # obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=15)).strftime('%Y-%m-%d')
                    obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=16)).strftime(
                        '%Y-%m-%d')  # cuong sua
                    obj1['lastinsp'] = equip.commissiondate.date().strftime('%Y-%m-%d')  # cuong them vao
                obj1['risk'] = round(obj1['df'] * obj1['gff'] * obj1['fms'] * obj1['fc'], 2)
                data.append(obj1)
        pagidata = Paginator(data, 25)
        pagedata = request.GET.get('page', 1)
        print(error)
        print(result)
        try:
            obj = pagidata.page(pagedata)
        except PageNotAnInteger:
            obj = pagidata.page(1)
        except EmptyPage:
            obj = pagedata.page(pagidata.num_pages)

        if comp.componenttypeid_id in tank:
            istank = 1
        else:
            istank = 0
        if comp.componenttypeid_id == 9 or comp.componenttypeid_id == 13:
            isshell = 1
        else:
            isshell = 0
        if request.POST:
            if '_delete' in request.POST:
                for a in rwass:
                    if request.POST.get('%d' % a.id):
                        a.delete()
                return redirect('proposalDisplay', componentID=componentID)
            if '_cancel' in request.POST:
                return redirect('proposalDisplay', componentID=componentID)
            if '_edit' in request.POST:
                for a in rwass:
                    if request.POST.get('%d' % a.id):
                        if istank:  # tuansua
                            print("tank")
                            return redirect('tankEdit', proposalID=a.id)
                        elif isshell:
                            print("tank")
                            return redirect('tankEdit', proposalID=a.id)
                        else:
                            print("nottank")
                            return redirect('prosalEdit', proposalID=a.id)
            if '_new' in request.POST:
                try:
                    if api.apicomponenttypename == 'TANKBOTTOM':
                        return redirect('tankNew', componentID=componentID)
                    elif isshell:
                        return redirect('tankNew', componentID=componentID)
                    else:
                        return redirect('proposalNew', componentID=componentID)
                except Exception as e:
                    print(e)
                    raise Http404
            if '_newscada' in request.POST and request.FILES['myexcelFile']:
                print("newscada")
                try:
                    for a in rwass:
                        if request.POST.get('%d' % a.id):
                            print(a.id)
                            myfile = request.FILES['myexcelFile']
                            fs = FileSystemStorage()
                            filename = fs.save(myfile.name, myfile)
                            uploaded_file_url = fs.url(filename)
                            url_file = settings.BASE_DIR.replace('\\', '//') + str(uploaded_file_url).replace('/',
                                                                                                              '//').replace(
                                '%20', ' ')
                            ExcelImport.ImportSCADA(url_file, a.id)
                except Exception as e:
                    print(e)
            if '_recal' in request.POST:
                for a in rwass:
                    if request.POST.get('%d' % a.id):
                        ReCalculate.ReCalculate(a.id)
                return redirect('proposalDisplay', componentID=componentID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/proposal/proposalListDisplay.html',
                  {'page': 'listProposal', 'obj': obj, 'istank': istank, 'isshell': isshell,
                   'componentID': componentID,'error':error,'result':result,
                   'equipmentID': comp.equipmentid_id, 'comp': comp, 'equip': equip, 'faci': faci,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def NewProposal(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        Fluid = ["Acid", "AlCl3", "C1-C2", "C13-C16", "C17-C25", "C25+", "C3-C4", "C5", "C6-C8", "C9-C12", "CO", "DEE",
                 "EE", "EEA", "EG", "EO", "H2", "H2S", "HCl", "HF", "Methanol", "Nitric Acid", "NO2", "Phosgene", "PO",
                 "Pyrophoric", "Steam", "Styrene", "TDI", "Water", "Caustic", "Aromatics", "Ammonia", "Chlorine"]
        ToxicFluid = ["H2S", "HF Acid", "CO", "HCl", "Nitric Acid", "AlCl3", "NO2", "Phosgene", "TDI", "PO", "EE",
                      "EO", "Pyrophoric", "Ammonia", "Chlorine"]
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        target = models.FacilityRiskTarget.objects.get(
            facilityid=models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id).facilityid_id)
        datafaci = models.Facility.objects.get(
            facilityid=models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id).facilityid_id)
        data = {}
        if request.method == 'POST':
            data['assessmentname'] = request.POST.get('AssessmentName')
            data['assessmentdate'] = request.POST.get('assessmentdate')
            data['assessmentmethod'] = request.POST.get('AssessmentMethod')
            data['apicomponenttypeid'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
            data['equipmentType'] = models.EquipmentType.objects.get(equipmenttypeid=models.EquipmentMaster.objects.get(
                equipmentid=comp.equipmentid_id).equipmenttypeid_id).equipmenttypename
            data['riskperiod'] = request.POST.get('RiskAnalysisPeriod')
            if request.POST.get('adminControlUpset'):
                adminControlUpset = 1
            else:
                adminControlUpset = 0

            if request.POST.get('ContainsDeadlegs'):
                containsDeadlegs = 1
            else:
                containsDeadlegs = 0

            if request.POST.get('Highly'):
                HighlyEffe = 1
            else:
                HighlyEffe = 0
            if request.POST.get('CylicOper'):
                cylicOp = 1
            else:
                cylicOp = 0

            if request.POST.get('Downtime'):
                downtime = 1
            else:
                downtime = 0

            if request.POST.get('SteamedOut'):
                steamOut = 1
            else:
                steamOut = 0

            if request.POST.get('HeatTraced'):
                heatTrace = 1
            else:
                heatTrace = 0

            if request.POST.get('PWHT'):
                pwht = 1
            else:
                pwht = 0

            if request.POST.get('InterfaceSoilWater'):
                interfaceSoilWater = 1
            else:
                interfaceSoilWater = 0

            if request.POST.get('PressurisationControlled'):
                pressureControl = 1
            else:
                pressureControl = 0

            if request.POST.get('LOM'):
                linerOnlineMoniter = 1
            else:
                linerOnlineMoniter = 0

            if request.POST.get('EquOper'):
                lowestTemp = 1
            else:
                lowestTemp = 0

            if request.POST.get('PresenceofSulphidesShutdow'):
                presentSulphidesShutdown = 1
            else:
                presentSulphidesShutdown = 0

            if request.POST.get('MFTF'):
                materialExposed = 1
            else:
                materialExposed = 0

            if request.POST.get('PresenceofSulphides'):
                presentSulphide = 1
            else:
                presentSulphide = 0

            data['minTemp'] = request.POST.get('Min')
            data['ExternalEnvironment'] = request.POST.get('ExternalEnvironment')
            data['ThermalHistory'] = request.POST.get('ThermalHistory')
            data['OnlineMonitoring'] = request.POST.get('OnlineMonitoring')
            data['EquipmentVolumn'] = request.POST.get('EquipmentVolume')

            ### component properties
            data['normaldiameter'] = request.POST.get('NominalDiameter')
            data['normalthick'] = request.POST.get('NominalThickness')
            data['currentthick'] = request.POST.get('CurrentThickness')
            data['tmin'] = request.POST.get('tmin')
            data['currentrate'] = request.POST.get('CurrentRate')
            data['deltafatt'] = request.POST.get('DeltaFATT')
            data['weldjointeff'] = request.POST.get('WeldJointEff')
            data['allowablestresss'] = request.POST.get('AllowableStress')
            data['structuralthickness'] = request.POST.get('StructuralThickness')
            data['compvolume'] = request.POST.get('CompVolume')
            if request.POST.get('DFDI'):
                damageDuringInsp = 1
            else:
                damageDuringInsp = 0

            if request.POST.get('ChemicalInjection'):
                chemicalInj = 1
            else:
                chemicalInj = 0

            if request.POST.get('PresenceCracks'):
                crackpresent = 1
            else:
                crackpresent = 0

            if request.POST.get('HFICI'):
                HFICI = 1
            else:
                HFICI = 0

            if request.POST.get('HTHADamage'):
                hthadamage = 1
            else:
                hthadamage = 0

            if request.POST.get('MinStructural'):
                minstruc = 1
            else:
                minstruc = 0

            if request.POST.get('P1AndP3'):
                p1andp3 = 1
            else:
                p1andp3 = 0

            if request.POST.get('EquipmentRequirements'):
                equipmentrequire = 1
            else:
                equipmentrequire = 0

            if request.POST.get('OperatingConditions'):
                operatingcondition = 1
            else:
                operatingcondition = 0

            if request.POST.get('CETtheMAWP'):
                cet = 1
            else:
                cet = 0

            if request.POST.get('CyclicService'):
                cyclicservice = 1
            else:
                cyclicservice = 0

            if request.POST.get('EquipmentorCircuit'):
                equipmentorCircuit = 1
            else:
                equipmentorCircuit = 0

            data['MaxBrinell'] = request.POST.get('MBHW')
            data['complex'] = request.POST.get('ComplexityProtrusions')
            data['CylicLoad'] = request.POST.get('CLC')
            data['branchDiameter'] = request.POST.get('BranchDiameter')
            data['joinTypeBranch'] = request.POST.get('JTB')
            data['numberPipe'] = request.POST.get('NFP')
            data['pipeCondition'] = request.POST.get('PipeCondition')
            data['prevFailure'] = request.POST.get('PreviousFailures')

            if request.POST.get('VASD'):
                visibleSharkingProtect = 1
            else:
                visibleSharkingProtect = 0

            data['shakingPipe'] = request.POST.get('ASP')
            data['timeShakingPipe'] = request.POST.get('ATSP')
            data['correctActionMitigate'] = request.POST.get('CAMV')
            data['confidencecr'] = request.POST.get('ConfidenceCR')

            # OP condition
            data['maxOT'] = request.POST.get('MaxOT')
            data['maxOP'] = request.POST.get('MaxOP')
            data['minOT'] = request.POST.get('MinOT')
            data['minOP'] = request.POST.get('MinOP')
            data['OpHydroPressure'] = request.POST.get('OHPP')
            data['criticalTemp'] = request.POST.get('CET')
            data['flowrate'] = request.POST.get('FlowRate')
            data['OP1'] = request.POST.get('Operating1')
            data['OP2'] = request.POST.get('Operating2')
            data['OP3'] = request.POST.get('Operating3')
            data['OP4'] = request.POST.get('Operating4')
            data['OP5'] = request.POST.get('Operating5')
            data['OP6'] = request.POST.get('Operating6')
            data['OP7'] = request.POST.get('Operating7')
            data['OP8'] = request.POST.get('Operating8')
            data['OP9'] = request.POST.get('Operating9')
            data['OP10'] = request.POST.get('Operating10')

            # material
            data['material'] = request.POST.get('Material')
            data['maxDesignTemp'] = request.POST.get('MaxDesignTemp')
            data['minDesignTemp'] = request.POST.get('MinDesignTemp')
            data['designPressure'] = request.POST.get('DesignPressure')
            data['tempRef'] = request.POST.get('ReferenceTemperature')
            data['BrittleFacture'] = request.POST.get('BFGT')
            data['CA'] = request.POST.get('CorrosionAllowance')
            data['sigmaPhase'] = request.POST.get('SigmaPhase')
            data['yieldstrength'] = request.POST.get('YieldStrength')
            data['tensilestrength'] = request.POST.get('TensileStrength')
            if request.POST.get('CoLAS'):
                cacbonAlloy = 1
            else:
                cacbonAlloy = 0

            if request.POST.get('AusteniticSteel'):
                austeniticStell = 1
            else:
                austeniticStell = 0

            if request.POST.get('SusceptibleTemper'):
                suscepTemp = 1
            else:
                suscepTemp = 0

            if request.POST.get('NickelAlloy'):
                nickelAlloy = 1
            else:
                nickelAlloy = 0

            if request.POST.get('Chromium'):
                chromium = 1
            else:
                chromium = 0

            data['sulfurContent'] = request.POST.get('SulfurContent')
            data['heatTreatment'] = request.POST.get('heatTreatment')

            if request.POST.get('MGTEHTHA'):
                materialHTHA = 1
            else:
                materialHTHA = 0

            data['HTHAMaterialGrade'] = request.POST.get('HTHAMaterialGrade')

            if request.POST.get('MaterialPTA'):
                materialPTA = 1
            else:
                materialPTA = 0

            data['PTAMaterialGrade'] = request.POST.get('PTAMaterialGrade')
            data['materialCostFactor'] = request.POST.get('MaterialCostFactor')

            # Coating, Clading
            if request.POST.get('InternalCoating'):
                InternalCoating = 1
            else:
                InternalCoating = 0

            if request.POST.get('ExternalCoating'):
                ExternalCoating = 1
            else:
                ExternalCoating = 0

            data['ExternalCoatingID'] = request.POST.get('ExternalCoatingID')
            data['ExternalCoatingQuality'] = request.POST.get('ExternalCoatingQuality')

            if request.POST.get('SCWD'):
                supportMaterial = 1
            else:
                supportMaterial = 0

            if request.POST.get('InternalCladding'):
                InternalCladding = 1
            else:
                InternalCladding = 0
            data['claddingthickness'] = request.POST.get('CladdingThickness')
            data['CladdingCorrosionRate'] = request.POST.get('CladdingCorrosionRate')

            if request.POST.get('InternalLining'):
                InternalLining = 1
            else:
                InternalLining = 0

            data['InternalLinerType'] = request.POST.get('InternalLinerType')
            data['InternalLinerCondition'] = request.POST.get('InternalLinerCondition')

            if request.POST.get('ExternalInsulation') == "on" or request.POST.get('ExternalInsulation') == 1:
                ExternalInsulation = 1
            else:
                ExternalInsulation = 0

            if request.POST.get('ICC'):
                InsulationCholride = 1
            else:
                InsulationCholride = 0

            data['ExternalInsulationType'] = request.POST.get('ExternalInsulationType')
            data['InsulationCondition'] = request.POST.get('InsulationCondition')

            # Steam
            data['NaOHConcentration'] = request.POST.get('NaOHConcentration')
            data['ReleasePercentToxic'] = request.POST.get('RFPT')
            data['ChlorideIon'] = request.POST.get('ChlorideIon')
            data['CO3'] = request.POST.get('CO3')
            data['H2SContent'] = request.POST.get('H2SContent')
            data['PHWater'] = request.POST.get('PHWater')

            if request.POST.get('EAGTA'):
                exposureAcid = 1
            else:
                exposureAcid = 0

            if request.POST.get('ToxicConstituents'):
                ToxicConstituents = 1
            else:
                ToxicConstituents = 0

            data['ExposureAmine'] = request.POST.get('ExposureAmine')
            data['AminSolution'] = request.POST.get('ASC')

            if request.POST.get('APDO'):
                aquaDuringOP = 1
            else:
                aquaDuringOP = 0

            if request.POST.get('APDSD'):
                aquaDuringShutdown = 1
            else:
                aquaDuringShutdown = 0

            if request.POST.get('EnvironmentCH2S'):
                EnvironmentCH2S = 1
            else:
                EnvironmentCH2S = 0

            if request.POST.get('PHA'):
                presentHF = 1
            else:
                presentHF = 0

            if request.POST.get('PresenceCyanides'):
                presentCyanide = 1
            else:
                presentCyanide = 0

            if request.POST.get('PCH'):
                processHydrogen = 1
            else:
                processHydrogen = 0

            if request.POST.get('ECCAC'):
                environCaustic = 1
            else:
                environCaustic = 0

            if request.POST.get('ESBC'):
                exposedSulfur = 1
            else:
                exposedSulfur = 0

            if request.POST.get('MEFMSCC'):
                materialExposedFluid = 1
            else:
                materialExposedFluid = 0
            # CA
            data['ModelFluid'] = request.POST.get('APIFluid')
            data['MassInventory'] = request.POST.get('MassInventory')
            data['ToxicFluid'] = request.POST.get('ToxicFluid')
            data['ToxicFluidPercent'] = request.POST.get('ToxicFluidPercent')
            data['PhaseStorage'] = request.POST.get('phaseOfFluid')
            data['LiquidLevel'] = request.POST.get('LiquidLevel')
            data['MassComponent'] = request.POST.get('MassComponent')
            data['EquipmentCost'] = request.POST.get('EquipmentCost')
            data['MittigationSystem'] = request.POST.get('MittigationSystem')
            data['ProductionCost'] = request.POST.get('ProductionCost')
            data['InjureCost'] = request.POST.get('InjureCost')
            data['ReleaseDuration'] = request.POST.get('ReleaseDuration')
            data['EnvironmentCost'] = request.POST.get('EnvironmentCost')
            data['PersonDensity'] = request.POST.get('PersonDensity')
            data['ProcessUnit'] = request.POST.get('ProcessUnit')
            data['OutageMulti'] = request.POST.get('OutageMulti')
            if request.POST.get(
                    'DetectionType') == "Intrumentation designed specifically to detect material losses by changes in operating conditions (i.e loss of pressure or flow) in the system":
                detectiontype = 'A'
            elif request.POST.get(
                    'DetectionType') == "Suitably located detectors to determine when the material is present outside the pressure-containing envelope":
                detectiontype = 'B'
            else:
                detectiontype = 'C'
            data['DetectionType'] = detectiontype
            if request.POST.get(
                    'IsolationType') == "Isolation or shutdown systerms activated directly from process instrumentation or detectors, with no operator intervention":
                isolationtype = 'A'
            elif request.POST.get(
                    'IsolationType') == "Isolation or shutdown systems activated by operators in the control room or other suitable locations remote from the leak":
                isolationtype = 'B'
            else:
                isolationtype = 'C'
            data['IsolationType'] = isolationtype
            if request.POST.get(
                    'MitigationSystem') == "Inventory blowdown, couple with isolation system activated remotely or automatically":
                mitigationsystem = 0.25
            elif request.POST.get('MitigationSystem') == "Fire water deluge system and monitors":
                mitigationsystem = 0.2
            elif request.POST.get('MitigationSystem') == "Fire water monitors only":
                mitigationsystem = 0.05
            else:
                mitigationsystem = 0.15
            data['MitigationSystem'] = mitigationsystem
            rwassessment = models.RwAssessment(equipmentid_id=comp.equipmentid_id, componentid_id=comp.componentid,
                                               assessmentdate=data['assessmentdate'],
                                               riskanalysisperiod=data['riskperiod'],
                                               isequipmentlinked=comp.isequipmentlinked,
                                               assessmentmethod=data['assessmentmethod'],
                                               proposalname=data['assessmentname'])
            rwassessment.save()
            rwequipment = models.RwEquipment(id=rwassessment, commissiondate=models.EquipmentMaster.objects.get(
                equipmentid=comp.equipmentid_id).commissiondate,
                                             adminupsetmanagement=adminControlUpset, containsdeadlegs=containsDeadlegs,
                                             cyclicoperation=cylicOp, highlydeadleginsp=HighlyEffe,
                                             downtimeprotectionused=downtime,
                                             externalenvironment=data['ExternalEnvironment'],
                                             heattraced=heatTrace, interfacesoilwater=interfaceSoilWater,
                                             lineronlinemonitoring=linerOnlineMoniter,
                                             materialexposedtoclext=materialExposed,
                                             minreqtemperaturepressurisation=data['minTemp'],
                                             onlinemonitoring=data['OnlineMonitoring'],
                                             presencesulphideso2=presentSulphide,
                                             presencesulphideso2shutdown=presentSulphidesShutdown,
                                             pressurisationcontrolled=pressureControl, pwht=pwht,
                                             steamoutwaterflush=steamOut,
                                             managementfactor=datafaci.managementfactor,
                                             thermalhistory=data['ThermalHistory'],
                                             yearlowestexptemp=lowestTemp, volume=data['EquipmentVolumn'])
            rwequipment.save()
            rwcomponent = models.RwComponent(id=rwassessment, nominaldiameter=data['normaldiameter'],
                                             nominalthickness=data['normalthick'],
                                             currentthickness=data['currentthick'],
                                             minreqthickness=data['tmin'], currentcorrosionrate=data['currentrate'],
                                             branchdiameter=data['branchDiameter'],
                                             branchjointtype=data['joinTypeBranch'],
                                             brinnelhardness=data['MaxBrinell'],
                                             brittlefracturethickness=data['BrittleFacture'],
                                             deltafatt=data['deltafatt'], chemicalinjection=chemicalInj,
                                             highlyinjectioninsp=HFICI, complexityprotrusion=data['complex'],
                                             correctiveaction=data['correctActionMitigate'], crackspresent=crackpresent,
                                             cyclicloadingwitin15_25m=data['CylicLoad'],
                                             damagefoundinspection=damageDuringInsp,
                                             numberpipefittings=data['numberPipe'],
                                             pipecondition=data['pipeCondition'],
                                             previousfailures=data['prevFailure'], shakingamount=data['shakingPipe'],
                                             shakingdetected=visibleSharkingProtect,
                                             shakingtime=data['timeShakingPipe'],
                                             weldjointefficiency=data['weldjointeff'],
                                             allowablestress=data['allowablestresss'],
                                             structuralthickness=data['structuralthickness'],
                                             componentvolume=data['compvolume'], hthadamage=hthadamage,
                                             minstructuralthickness=minstruc,
                                             fabricatedsteel=p1andp3, equipmentsatisfied=equipmentrequire,
                                             nominaloperatingconditions=operatingcondition,
                                             cetgreaterorequal=cet, cyclicservice=cyclicservice,
                                             equipmentcircuitshock=equipmentorCircuit,
                                             confidencecorrosionrate=data['confidencecr'])
            rwcomponent.save()
            rwstream = models.RwStream(id=rwassessment, aminesolution=data['AminSolution'],
                                       aqueousoperation=aquaDuringOP,
                                       aqueousshutdown=aquaDuringShutdown, toxicconstituent=ToxicConstituents,
                                       caustic=environCaustic,
                                       chloride=data['ChlorideIon'], co3concentration=data['CO3'],
                                       cyanide=presentCyanide,
                                       exposedtogasamine=exposureAcid, exposedtosulphur=exposedSulfur,
                                       exposuretoamine=data['ExposureAmine'],
                                       h2s=EnvironmentCH2S, h2sinwater=data['H2SContent'], hydrogen=processHydrogen,
                                       hydrofluoric=presentHF, materialexposedtoclint=materialExposedFluid,
                                       maxoperatingpressure=data['maxOP'],
                                       maxoperatingtemperature=float(data['maxOT']),
                                       minoperatingpressure=float(data['minOP']),
                                       minoperatingtemperature=data['minOT'],
                                       criticalexposuretemperature=data['criticalTemp'],
                                       naohconcentration=data['NaOHConcentration'],
                                       releasefluidpercenttoxic=float(data['ReleasePercentToxic']),
                                       waterph=float(data['PHWater']),
                                       h2spartialpressure=float(data['OpHydroPressure']),
                                       flowrate=float(data['flowrate']), liquidlevel=float(data['LiquidLevel']),
                                       storagephase=data['PhaseStorage'])
            rwstream.save()
            rwexcor = models.RwExtcorTemperature(id=rwassessment, minus12tominus8=data['OP1'],
                                                 minus8toplus6=data['OP2'],
                                                 plus6toplus32=data['OP3'], plus32toplus71=data['OP4'],
                                                 plus71toplus107=data['OP5'],
                                                 plus107toplus121=data['OP6'], plus121toplus135=data['OP7'],
                                                 plus135toplus162=data['OP8'], plus162toplus176=data['OP9'],
                                                 morethanplus176=data['OP10'])
            rwexcor.save()
            rwcoat = models.RwCoating(id=rwassessment, externalcoating=ExternalCoating,
                                      externalinsulation=ExternalInsulation,
                                      internalcladding=InternalCladding, internalcoating=InternalCoating,
                                      internallining=InternalLining,
                                      externalcoatingdate=data['ExternalCoatingID'],
                                      externalcoatingquality=data['ExternalCoatingQuality'],
                                      externalinsulationtype=data['ExternalInsulationType'],
                                      insulationcondition=data['InsulationCondition'],
                                      insulationcontainschloride=InsulationCholride,
                                      internallinercondition=data['InternalLinerCondition'],
                                      internallinertype=data['InternalLinerType'],
                                      claddingcorrosionrate=data['CladdingCorrosionRate'],
                                      supportconfignotallowcoatingmaint=supportMaterial,
                                      claddingthickness=data['claddingthickness'])
            rwcoat.save()

            rwmaterial = models.RwMaterial(id=rwassessment, corrosionallowance=data['CA'],
                                           materialname=data['material'],
                                           designpressure=data['designPressure'],
                                           designtemperature=data['maxDesignTemp'],
                                           mindesigntemperature=data['minDesignTemp'],
                                           sigmaphase=data['sigmaPhase'],
                                           sulfurcontent=data['sulfurContent'], heattreatment=data['heatTreatment'],
                                           referencetemperature=data['tempRef'],
                                           ptamaterialcode=data['PTAMaterialGrade'],
                                           hthamaterialcode=data['HTHAMaterialGrade'], ispta=materialPTA,
                                           ishtha=materialHTHA,
                                           austenitic=austeniticStell, temper=suscepTemp, carbonlowalloy=cacbonAlloy,
                                           nickelbased=nickelAlloy, chromemoreequal12=chromium,
                                           costfactor=data['materialCostFactor'],
                                           yieldstrength=data['yieldstrength'], tensilestrength=data['tensilestrength'])
            rwmaterial.save()
            rwinputca = models.RwInputCaLevel1(id=rwassessment,
                                               release_duration=data['ReleaseDuration'],
                                               detection_type=data['DetectionType'],
                                               isulation_type=data['IsolationType'],
                                               mitigation_system=data['MittigationSystem'],
                                               equipment_cost=data['EquipmentCost'], injure_cost=data['InjureCost'],
                                               evironment_cost=data['EnvironmentCost'],
                                               personal_density=data['PersonDensity'],
                                               material_cost=data['materialCostFactor'],
                                               production_cost=data['ProductionCost'],
                                               mass_inventory=data['MassInventory'],
                                               mass_component=data['MassComponent'],
                                               stored_pressure=float(data['minOP']) * 6.895, stored_temp=data['minOT'],
                                               model_fluid=data['ModelFluid'], toxic_fluid=data['ToxicFluid'],
                                               toxic_percent=float(data['ToxicFluidPercent']),
                                               process_unit=float(data['ProcessUnit']),
                                               outage_multiplier=float(data['OutageMulti']))
            rwinputca.save()
            ReCalculate.ReCalculate(rwassessment.id)
            return redirect('damgeFactor', proposalID=rwassessment.id)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/proposal/proposalNormalNew.html',
                  {'page': 'newProposal', 'api': Fluid, 'componentID': componentID, 'equipmentID': comp.equipmentid_id,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count,
                   'toxicfluid': ToxicFluid})


def NewTank(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        eq = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
        target = models.FacilityRiskTarget.objects.get(facilityid=eq.facilityid_id)
        datafaci = models.Facility.objects.get(facilityid=eq.facilityid_id)
        data = {}
        isshell = False
        if comp.componenttypeid_id == 8 or comp.componenttypeid_id == 14:
            isshell = True
        if request.method == 'POST':
            # Data Assessment
            data['confidencecr'] = request.POST.get('ConfidenceCR')  # bo sung level of confident for tankbottom
            data['assessmentName'] = request.POST.get('AssessmentName')
            data['assessmentdate'] = request.POST.get('assessmentdate')
            data['riskperiod'] = request.POST.get('RiskAnalysisPeriod')
            data['assessmentmethod'] = request.POST.get('AssessmentMethod')
            data['apicomponenttypeid'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
            data['equipmenttype'] = models.EquipmentType.objects.get(
                equipmenttypeid=eq.equipmenttypeid_id).equipmenttypename
            # Data Equipment Properties
            if request.POST.get('Admin'):
                adminControlUpset = 1
            else:
                adminControlUpset = 0

            if request.POST.get('CylicOper'):
                cylicOp = 1
            else:
                cylicOp = 0

            if request.POST.get('Highly'):
                highlyDeadleg = 1
            else:
                highlyDeadleg = 0

            if request.POST.get('Steamed'):
                steamOutWater = 1
            else:
                steamOutWater = 0
            if request.POST.get('Downtime'):
                downtimeProtect = 1
            else:
                downtimeProtect = 0

            if request.POST.get('PWHT'):
                pwht = 1
            else:
                pwht = 0

            if request.POST.get('HeatTraced'):
                heatTrace = 1
            else:
                heatTrace = 0

            data['distance'] = request.POST.get('Distance')

            if request.POST.get('InterfaceSoilWater'):
                interfaceSoilWater = 1
            else:
                interfaceSoilWater = 0

            data['soiltype'] = request.POST.get('typeofSoil')

            if request.POST.get('PressurisationControlled'):
                pressureControl = 1
            else:
                pressureControl = 0

            data['minRequireTemp'] = request.POST.get('MinReq')

            if request.POST.get('lowestTemp'):
                lowestTemp = 1
            else:
                lowestTemp = 0

            if request.POST.get('MFTF'):
                materialChlorineExt = 1
            else:
                materialChlorineExt = 0

            if request.POST.get('LOM'):
                linerOnlineMonitor = 1
            else:
                linerOnlineMonitor = 0

            if request.POST.get('PresenceofSulphides'):
                presenceSulphideOP = 1
            else:
                presenceSulphideOP = 0

            if request.POST.get('PresenceofSulphidesShutdow'):
                presenceSulphideShut = 1
            else:
                presenceSulphideShut = 0

            if request.POST.get('ComponentWelded'):
                componentWelded = 1
            else:
                componentWelded = 0

            if request.POST.get('TMA'):
                tankIsMaintain = 1
            else:
                tankIsMaintain = 0

            data['adjustSettlement'] = request.POST.get('AdjForSettlement')
            data['extEnvironment'] = request.POST.get('ExternalEnvironment')
            data['EnvSensitivity'] = request.POST.get('EnvironmentSensitivity')
            data['themalHistory'] = request.POST.get('ThermalHistory')
            data['onlineMonitor'] = request.POST.get('OnlineMonitoring')
            data['equipmentVolumn'] = request.POST.get('EquipmentVolume')
            # Component Properties
            data['structuralthickness'] = request.POST.get('StructuralThickness')
            data['tankDiameter'] = request.POST.get('TankDiameter')
            data['NominalThickness'] = request.POST.get('NominalThickness')
            data['currentThick'] = request.POST.get('CurrentThickness')
            data['minRequireThick'] = request.POST.get('MinReqThick')
            data['currentCorrosion'] = request.POST.get('CurrentCorrosionRate')
            data['ComponentVolume'] = request.POST.get('CompVolume')
            data['WeldJointEff'] = request.POST.get('WeldJointEff')
            data['HeightEShellC'] = request.POST.get('HeightEShellC')
            if request.POST.get('MinStructural'):
                minstruc = 1
            else:
                minstruc = 0
            if request.POST.get('DFDI'):
                damageFound = 1
            else:
                damageFound = 0

            if request.POST.get('PresenceCracks'):
                crackPresence = 1
            else:
                crackPresence = 0

            if request.POST.get('TrampElements'):
                trampElements = 1
            else:
                trampElements = 0

            if request.POST.get('ReleasePreventionBarrier'):
                preventBarrier = 1
            else:
                preventBarrier = 0

            if request.POST.get('ConcreteFoundation'):
                concreteFoundation = 1
            else:
                concreteFoundation = 0

            if request.POST.get('P1AndP3'):
                p1andp3 = 1
            else:
                p1andp3 = 0

            if request.POST.get('EquipmentRequirements'):
                equipmentrequire = 1
            else:
                equipmentrequire = 0

            if request.POST.get('OperatingConditions'):
                operatingcondition = 1
            else:
                operatingcondition = 0

            if request.POST.get('CETtheMAWP'):
                cet = 1
            else:
                cet = 0

            if request.POST.get('CyclicService'):
                cyclicservice = 1
            else:
                cyclicservice = 0

            if request.POST.get('EquipmentorCircuit'):
                equipmentorCircuit = 1
            else:
                equipmentorCircuit = 0

            data['maxBrinnelHardness'] = request.POST.get('MBHW')
            data['complexProtrusion'] = request.POST.get('ComplexityProtrusions')
            data['severityVibration'] = request.POST.get('SeverityVibration')

            # Operating condition
            data['maxOT'] = request.POST.get('MaxOT')
            data['maxOP'] = request.POST.get('MaxOP')
            data['minOT'] = request.POST.get('MinOT')
            data['minOP'] = request.POST.get('MinOP')
            data['H2Spressure'] = request.POST.get('OHPP')
            data['criticalTemp'] = request.POST.get('CET')
            data['flowrate'] = request.POST.get('FlowRate')
            data['OP1'] = request.POST.get('Operating1')
            data['OP2'] = request.POST.get('Operating2')
            data['OP3'] = request.POST.get('Operating3')
            data['OP4'] = request.POST.get('Operating4')
            data['OP5'] = request.POST.get('Operating5')
            data['OP6'] = request.POST.get('Operating6')
            data['OP7'] = request.POST.get('Operating7')
            data['OP8'] = request.POST.get('Operating8')
            data['OP9'] = request.POST.get('Operating9')
            data['OP10'] = request.POST.get('Operating10')

            # Material
            data['materialName'] = request.POST.get('materialname')
            data['maxDesignTemp'] = request.POST.get('MaxDesignTemp')
            data['minDesignTemp'] = request.POST.get('MinDesignTemp')
            data['designPressure'] = request.POST.get('DesignPressure')
            data['refTemp'] = request.POST.get('ReferenceTemperature')
            data['allowStress'] = request.POST.get('ASAT')
            data['brittleThick'] = request.POST.get('BFGT')
            data['corrosionAllow'] = request.POST.get('CorrosionAllowance')
            data['yieldstrength'] = request.POST.get('YieldStrength')
            data['tensilestrength'] = request.POST.get('TensileStrength')
            if request.POST.get('CoLAS'):
                carbonLowAlloySteel = 1
            else:
                carbonLowAlloySteel = 0

            if request.POST.get('AusteniticSteel'):
                austeniticSteel = 1
            else:
                austeniticSteel = 0

            if request.POST.get('NickelAlloy'):
                nickelAlloy = 1
            else:
                nickelAlloy = 0

            if request.POST.get('Chromium'):
                chromium = 1
            else:
                chromium = 0

            data['sulfurContent'] = request.POST.get('SulfurContent')
            data['heatTreatment'] = request.POST.get('heatTreatment')

            if request.POST.get('MGTEPTA'):
                materialPTA = 1
            else:
                materialPTA = 0

            data['PTAMaterialGrade'] = request.POST.get('PTAMaterialGrade')
            data['materialCostFactor'] = request.POST.get('MaterialCostFactor')
            data['productionCost'] = request.POST.get('ProductionCost')

            # Coating, Cladding
            if request.POST.get('InternalCoating'):
                internalCoating = 1
            else:
                internalCoating = 0

            if request.POST.get('ExternalCoating'):
                externalCoating = 1
            else:
                externalCoating = 0

            data['externalInstallDate'] = request.POST.get('ExternalCoatingID')
            data['externalCoatQuality'] = request.POST.get('ExternalCoatingQuality')

            if request.POST.get('SCWD'):
                supportCoatingMaintain = 1
            else:
                supportCoatingMaintain = 0

            if request.POST.get('InternalCladding'):
                internalCladding = 1
            else:
                internalCladding = 0
            data['CladdingThinkness'] = request.POST.get('CladdingThinkness')
            data['cladCorrosion'] = request.POST.get('CladdingCorrosionRate')

            if request.POST.get('InternalLining'):
                internalLinning = 1
            else:
                internalLinning = 0

            data['internalLinnerType'] = request.POST.get('InternalLinerType')
            data['internalLinnerCondition'] = request.POST.get('InternalLinerCondition')

            if request.POST.get('ExternalInsulation'):
                extInsulation = 1
            else:
                extInsulation = 0

            if request.POST.get('ICC'):
                InsulationContainChloride = 1
            else:
                InsulationContainChloride = 0

            data['extInsulationType'] = request.POST.get('ExternalInsulationType')
            data['insulationCondition'] = request.POST.get('InsulationCondition')
            # Stream
            data['fluid'] = request.POST.get('Fluid')
            data['fluidHeight'] = request.POST.get('FluidHeight')
            data['fluidLeaveDike'] = request.POST.get('PFLD')
            data['fluidOnsite'] = request.POST.get('PFLDRS')
            data['fluidOffsite'] = request.POST.get('PFLDGoffsite')
            data['naohConcent'] = request.POST.get('NaOHConcentration')
            data['releasePercentToxic'] = request.POST.get('RFPT')
            data['chlorideIon'] = request.POST.get('ChlorideIon')
            data['co3'] = request.POST.get('CO3')
            data['h2sContent'] = request.POST.get('H2SContent')
            data['PHWater'] = request.POST.get('PHWater')

            if request.POST.get('EAGTA'):
                exposedAmine = 1
            else:
                exposedAmine = 0

            data['amineSolution'] = request.POST.get('AmineSolution')
            data['exposureAmine'] = request.POST.get('ExposureAmine')

            if request.POST.get('APDO'):
                aqueosOP = 1
            else:
                aqueosOP = 0

            if request.POST.get('EnvironmentCH2S'):
                environtH2S = 1
            else:
                environtH2S = 0

            if request.POST.get('APDSD'):
                aqueosShut = 1
            else:
                aqueosShut = 0

            if request.POST.get('PresenceCyanides'):
                cyanidesPresence = 1
            else:
                cyanidesPresence = 0

            if request.POST.get('presenceHF'):
                presentHF = 1
            else:
                presentHF = 0

            if request.POST.get('ECCAC'):
                environtCaustic = 1
            else:
                environtCaustic = 0

            if request.POST.get('PCH'):
                processContainHydro = 1
            else:
                processContainHydro = 0

            if request.POST.get('MEFMSCC'):
                materialChlorineIntern = 1
            else:
                materialChlorineIntern = 0

            if request.POST.get('ESBC'):
                exposedSulfur = 1
            else:
                exposedSulfur = 0

            if str(data['fluid']) == "Gasoline":
                apiFluid = "C6-C8"
            elif str(data['fluid']) == "Light Diesel Oil":
                apiFluid = "C9-C12"
            elif str(data['fluid']) == "Heavy Diesel Oil":
                apiFluid = "C13-C16"
            elif str(data['fluid']) == "Fuel Oil" or str(data['fluid']) == "Crude Oil":
                apiFluid = "C17-C25"
            elif str(data['fluid']) == "Water":
                apiFluid = "Water"
            else:
                apiFluid = "C25+"
            rwassessment = models.RwAssessment(equipmentid_id=comp.equipmentid_id, componentid_id=comp.componentid,
                                               assessmentdate=data['assessmentdate'],
                                               riskanalysisperiod=data['riskperiod'],
                                               isequipmentlinked=comp.isequipmentlinked,
                                               proposalname=data['assessmentName'],
                                               assessmentmethod=data['assessmentmethod'])
            rwassessment.save()
            rwequipment = models.RwEquipment(id=rwassessment, commissiondate=eq.commissiondate,
                                             adminupsetmanagement=adminControlUpset,
                                             cyclicoperation=cylicOp, highlydeadleginsp=highlyDeadleg,
                                             downtimeprotectionused=downtimeProtect, steamoutwaterflush=steamOutWater,
                                             pwht=pwht, heattraced=heatTrace, distancetogroundwater=data['distance'],
                                             interfacesoilwater=interfaceSoilWater, typeofsoil=data['soiltype'],
                                             pressurisationcontrolled=pressureControl,
                                             minreqtemperaturepressurisation=data['minRequireTemp'],
                                             yearlowestexptemp=lowestTemp,
                                             materialexposedtoclext=materialChlorineExt,
                                             lineronlinemonitoring=linerOnlineMonitor,
                                             presencesulphideso2=presenceSulphideOP,
                                             presencesulphideso2shutdown=presenceSulphideShut,
                                             componentiswelded=componentWelded, tankismaintained=tankIsMaintain,
                                             adjustmentsettle=data['adjustSettlement'],
                                             externalenvironment=data['extEnvironment'],
                                             environmentsensitivity=data['EnvSensitivity'],
                                             onlinemonitoring=data['onlineMonitor'],
                                             thermalhistory=data['themalHistory'],
                                             managementfactor=datafaci.managementfactor,
                                             volume=data['equipmentVolumn'])
            rwequipment.save()
            rwcomponent = models.RwComponent(id=rwassessment, nominaldiameter=data['tankDiameter'],
                                             allowablestress=data['allowStress'],
                                             nominalthickness=data['NominalThickness'],
                                             currentthickness=data['currentThick'],
                                             minreqthickness=data['minRequireThick'],
                                             currentcorrosionrate=data['currentCorrosion'],
                                             shellheight=data['HeightEShellC'], damagefoundinspection=damageFound,
                                             crackspresent=crackPresence, componentvolume=data['ComponentVolume'],
                                             weldjointefficiency=data['WeldJointEff'],
                                             # trampelements=trampElements,
                                             brittlefracturethickness=data['brittleThick'],
                                             releasepreventionbarrier=preventBarrier,
                                             concretefoundation=concreteFoundation,
                                             brinnelhardness=data['maxBrinnelHardness'],
                                             structuralthickness=data['structuralthickness'],
                                             complexityprotrusion=data['complexProtrusion'],
                                             minstructuralthickness=minstruc,
                                             severityofvibration=data['severityVibration'],
                                             fabricatedsteel=p1andp3, equipmentsatisfied=equipmentrequire,
                                             nominaloperatingconditions=operatingcondition,
                                             cetgreaterorequal=cet, cyclicservice=cyclicservice,
                                             equipmentcircuitshock=equipmentorCircuit,
                                             confidencecorrosionrate=data['confidencecr'])
            rwcomponent.save()
            rwstream = models.RwStream(id=rwassessment, maxoperatingtemperature=data['maxOT'],
                                       maxoperatingpressure=data['maxOP'],
                                       minoperatingtemperature=data['minOT'], minoperatingpressure=data['minOP'],
                                       h2spartialpressure=data['H2Spressure'],
                                       criticalexposuretemperature=data['criticalTemp'],
                                       tankfluidname=data['fluid'], fluidheight=data['fluidHeight'],
                                       fluidleavedikepercent=data['fluidLeaveDike'],
                                       fluidleavedikeremainonsitepercent=data['fluidOnsite'],
                                       fluidgooffsitepercent=data['fluidOffsite'],
                                       naohconcentration=data['naohConcent'],
                                       releasefluidpercenttoxic=data['releasePercentToxic'],
                                       chloride=data['chlorideIon'], co3concentration=data['co3'],
                                       h2sinwater=data['h2sContent'],
                                       waterph=data['PHWater'], exposedtogasamine=exposedAmine,
                                       aminesolution=data['amineSolution'],
                                       exposuretoamine=data['exposureAmine'], aqueousoperation=aqueosOP,
                                       h2s=environtH2S,
                                       aqueousshutdown=aqueosShut, cyanide=cyanidesPresence, hydrofluoric=presentHF,
                                       caustic=environtCaustic, hydrogen=processContainHydro,
                                       materialexposedtoclint=materialChlorineIntern,
                                       exposedtosulphur=exposedSulfur, flowrate=float(data['flowrate']))
            rwstream.save()
            rwexcor = models.RwExtcorTemperature(id=rwassessment, minus12tominus8=data['OP1'],
                                                 minus8toplus6=data['OP2'],
                                                 plus6toplus32=data['OP3'], plus32toplus71=data['OP4'],
                                                 plus71toplus107=data['OP5'],
                                                 plus107toplus121=data['OP6'], plus121toplus135=data['OP7'],
                                                 plus135toplus162=data['OP8'], plus162toplus176=data['OP9'],
                                                 morethanplus176=data['OP10'])
            rwexcor.save()
            rwcoat = models.RwCoating(id=rwassessment, internalcoating=internalCoating, externalcoating=externalCoating,
                                      externalcoatingdate=data['externalInstallDate'],
                                      externalcoatingquality=data['externalCoatQuality'],
                                      supportconfignotallowcoatingmaint=supportCoatingMaintain,
                                      internalcladding=internalCladding,
                                      claddingcorrosionrate=data['cladCorrosion'], internallining=internalLinning,
                                      internallinertype=data['internalLinnerType'],
                                      internallinercondition=data['internalLinnerCondition'],
                                      externalinsulation=extInsulation,
                                      insulationcontainschloride=InsulationContainChloride,
                                      externalinsulationtype=data['extInsulationType'],
                                      insulationcondition=data['insulationCondition'],
                                      claddingthickness=data['CladdingThinkness']
                                      )
            rwcoat.save()
            rwmaterial = models.RwMaterial(id=rwassessment, materialname=data['materialName'],
                                           designtemperature=data['maxDesignTemp'],
                                           mindesigntemperature=data['minDesignTemp'],
                                           designpressure=data['designPressure'],
                                           referencetemperature=data['refTemp'],
                                           # allowablestress=data['allowStress'],
                                           corrosionallowance=data['corrosionAllow'],
                                           carbonlowalloy=carbonLowAlloySteel, austenitic=austeniticSteel,
                                           nickelbased=nickelAlloy,
                                           chromemoreequal12=chromium,
                                           sulfurcontent=data['sulfurContent'], heattreatment=data['heatTreatment'],
                                           ispta=materialPTA, ptamaterialcode=data['PTAMaterialGrade'],
                                           costfactor=data['materialCostFactor'], yieldstrength=data['yieldstrength'],
                                           tensilestrength=data['tensilestrength'])
            rwmaterial.save()
            rwinputca = models.RwInputCaTank(id=rwassessment, fluid_height=data['fluidHeight'],
                                             shell_course_height=data['HeightEShellC'],
                                             tank_diametter=data['tankDiameter'], prevention_barrier=preventBarrier,
                                             environ_sensitivity=data['EnvSensitivity'],
                                             p_lvdike=data['fluidLeaveDike'], p_offsite=data['fluidOffsite'],
                                             p_onsite=data['fluidOnsite'], soil_type=data['soiltype'],
                                             tank_fluid=data['fluid'], api_fluid=apiFluid, sw=data['distance'],
                                             productioncost=data['productionCost'])
            rwinputca.save()
            print()
            # Customize Caculate Here
            ReCalculate.ReCalculate(rwassessment.id)
            return redirect('damgeFactor', proposalID=rwassessment.id)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/proposal/proposalTankNew.html',
                  {'page': 'newProposal', 'isshell': isshell, 'componentID': componentID,
                   'equipmentID': comp.equipmentid_id, 'info': request.session, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def EditProposal(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        Fluid = ["Acid", "AlCl3", "C1-C2", "C13-C16", "C17-C25", "C25+", "C3-C4", "C5", "C6-C8", "C9-C12", "CO", "DEE",
                 "EE", "EEA", "EG", "EO", "H2", "H2S", "HCl", "HF", "Methanol", "Nitric Acid", "NO2", "Phosgene", "PO",
                 "Pyrophoric", "Steam", "Styrene", "TDI", "Water"]
        ToxicFluid = ["H2S", "HF Acid", "CO", "HCl", "Nitric Acid", "AlCl3", "NO2", "Phosgene", "TDI", "PO", "EE",
                      "EO", "Pyrophoric", "Ammonia", "Chlorine"]
        rwassessment = models.RwAssessment.objects.get(id=proposalID)
        rwequipment = models.RwEquipment.objects.get(id=proposalID)
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwstream = models.RwStream.objects.get(id=proposalID)
        rwexcor = models.RwExtcorTemperature.objects.get(id=proposalID)
        rwcoat = models.RwCoating.objects.get(id=proposalID)
        rwmaterial = models.RwMaterial.objects.get(id=proposalID)
        rwinputca = models.RwInputCaLevel1.objects.get(id=proposalID)
        assDate = rwassessment.assessmentdate.strftime('%Y-%m-%d')
        try:
            extDate = rwcoat.externalcoatingdate.strftime('%Y-%m-%d')
        except:
            extDate = datetime.now().strftime('%Y-%m-%d')

        comp = models.ComponentMaster.objects.get(componentid=rwassessment.componentid_id)
        data = {}
        if request.method == 'POST':
            data['assessmentname'] = request.POST.get('AssessmentName')
            data['assessmentdate'] = request.POST.get('assessmentdate')
            data['apicomponenttypeid'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
            data['equipmentType'] = models.EquipmentType.objects.get(equipmenttypeid=models.EquipmentMaster.objects.get(
                equipmentid=comp.equipmentid_id).equipmenttypeid_id).equipmenttypename
            data['riskperiod'] = request.POST.get('RiskAnalysisPeriod')

            if request.POST.get('P1AndP3'):
                p1andp3 = 1
            else:
                p1andp3 = 0

            if request.POST.get('EquipmentRequirements'):
                equipmentrequire = 1
            else:
                equipmentrequire = 0

            if request.POST.get('OperatingConditions'):
                operatingcondition = 1
            else:
                operatingcondition = 0

            if request.POST.get('CETtheMAWP'):
                cet = 1
            else:
                cet = 0

            if request.POST.get('CyclicService'):
                cyclicservice = 1
            else:
                cyclicservice = 0

            if request.POST.get('EquipmentorCircuit'):
                equipmentorCircuit = 1
            else:
                equipmentorCircuit = 0

            if request.POST.get('EquipmentorCircuit'):
                equipmentorCircuit = 1
            else:
                equipmentorCircuit = 0

            if request.POST.get('MinStructural'):
                minstruc = 1
            else:
                minstruc = 0

            if request.POST.get('HTHADamage'):
                hthadamage = 1
            else:
                hthadamage = 0

            if request.POST.get('adminControlUpset'):
                adminControlUpset = 1
            else:
                adminControlUpset = 0

            if request.POST.get('ContainsDeadlegs'):
                containsDeadlegs = 1
            else:
                containsDeadlegs = 0

            if request.POST.get('Highly'):
                HighlyEffe = 1
            else:
                HighlyEffe = 0

            if request.POST.get('CylicOper'):
                cylicOP = 1
            else:
                cylicOP = 0

            if request.POST.get('Downtime'):
                downtime = 1
            else:
                downtime = 0

            if request.POST.get('SteamedOut'):
                steamOut = 1
            else:
                steamOut = 0

            if request.POST.get('HeatTraced'):
                heatTrace = 1
            else:
                heatTrace = 0

            if request.POST.get('PWHT'):
                pwht = 1
            else:
                pwht = 0

            if request.POST.get('InterfaceSoilWater'):
                interfaceSoilWater = 1
            else:
                interfaceSoilWater = 0

            if request.POST.get('PressurisationControlled'):
                pressureControl = 1
            else:
                pressureControl = 0

            if request.POST.get('LOM'):
                linerOnlineMoniter = 1
            else:
                linerOnlineMoniter = 0

            if request.POST.get('EquOper'):
                lowestTemp = 1
            else:
                lowestTemp = 0

            if request.POST.get('PresenceofSulphidesShutdow'):
                presentSulphidesShutdown = 1
            else:
                presentSulphidesShutdown = 0

            if request.POST.get('MFTF'):
                materialExposed = 1
            else:
                materialExposed = 0

            if request.POST.get('PresenceofSulphides'):
                presentSulphide = 1
            else:
                presentSulphide = 0

            data['minTemp'] = request.POST.get('Min')
            data['ExternalEnvironment'] = request.POST.get('ExternalEnvironment')
            data['ThermalHistory'] = request.POST.get('ThermalHistory')
            data['OnlineMonitoring'] = request.POST.get('OnlineMonitoring')
            data['EquipmentVolumn'] = request.POST.get('EquipmentVolume')

            data['normaldiameter'] = request.POST.get('NominalDiameter')
            data['normalthick'] = request.POST.get('NominalThickness')
            data['currentthick'] = request.POST.get('CurrentThickness')
            data['tmin'] = request.POST.get('tmin')
            data['currentrate'] = request.POST.get('CurrentRate')
            data['deltafatt'] = request.POST.get('DeltaFATT')
            data['weldjointeff'] = request.POST.get('WeldJointEff')
            data['structuralthickness'] = request.POST.get('StructuralThickness')
            data['compvolume'] = request.POST.get('CompVolume')
            data['allowStress'] = request.POST.get('AllowableStress')
            if request.POST.get('DFDI'):
                damageDuringInsp = 1
            else:
                damageDuringInsp = 0

            if request.POST.get('ChemicalInjection'):
                chemicalInj = 1
            else:
                chemicalInj = 0

            if request.POST.get('PresenceCracks'):
                crackpresent = 1
            else:
                crackpresent = 0

            if request.POST.get('HFICI'):
                HFICI = 1
            else:
                HFICI = 0

            if request.POST.get('TrampElements'):
                TrampElement = 1
            else:
                TrampElement = 0

            data['MaxBrinell'] = request.POST.get('MBHW')
            data['complex'] = request.POST.get('ComplexityProtrusions')
            data['CylicLoad'] = request.POST.get('CLC')
            data['branchDiameter'] = request.POST.get('BranchDiameter')
            data['joinTypeBranch'] = request.POST.get('JTB')
            data['numberPipe'] = request.POST.get('NFP')
            data['pipeCondition'] = request.POST.get('PipeCondition')
            data['prevFailure'] = request.POST.get('PreviousFailures')

            if request.POST.get('VASD'):
                visibleSharkingProtect = 1
            else:
                visibleSharkingProtect = 0

            data['shakingPipe'] = request.POST.get('ASP')
            data['timeShakingPipe'] = request.POST.get('ATSP')
            data['correctActionMitigate'] = request.POST.get('CAMV')
            # OP condition
            data['maxOT'] = request.POST.get('MaxOT')
            data['maxOP'] = request.POST.get('MaxOP')
            data['minOT'] = request.POST.get('MinOT')
            data['minOP'] = request.POST.get('MinOP')
            data['OpHydroPressure'] = request.POST.get('OHPP')
            data['criticalTemp'] = request.POST.get('CET')
            data['OP1'] = request.POST.get('Operating1')
            data['OP2'] = request.POST.get('Operating2')
            data['OP3'] = request.POST.get('Operating3')
            data['OP4'] = request.POST.get('Operating4')
            data['OP5'] = request.POST.get('Operating5')
            data['OP6'] = request.POST.get('Operating6')
            data['OP7'] = request.POST.get('Operating7')
            data['OP8'] = request.POST.get('Operating8')
            data['OP9'] = request.POST.get('Operating9')
            data['OP10'] = request.POST.get('Operating10')
            # material
            data['material'] = request.POST.get('Material')
            data['maxDesignTemp'] = request.POST.get('MaxDesignTemp')
            data['minDesignTemp'] = request.POST.get('MinDesignTemp')
            data['designPressure'] = request.POST.get('DesignPressure')
            data['tempRef'] = request.POST.get('ReferenceTemperature')
            # data['allowStress'] = request.POST.get('ASAT')
            data['BrittleFacture'] = request.POST.get('BFGT')
            data['CA'] = request.POST.get('CorrosionAllowance')
            data['sigmaPhase'] = request.POST.get('SigmaPhase')
            data['yieldstrength'] = request.POST.get('YieldStrength')
            data['tensilestrength'] = request.POST.get('TensileStrength')
            if request.POST.get('CoLAS'):
                cacbonAlloy = 1
            else:
                cacbonAlloy = 0

            if request.POST.get('AusteniticSteel'):
                austeniticStell = 1
            else:
                austeniticStell = 0

            if request.POST.get('SusceptibleTemper'):
                suscepTemp = 1
            else:
                suscepTemp = 0

            if request.POST.get('NickelAlloy'):
                nickelAlloy = 1
            else:
                nickelAlloy = 0

            if request.POST.get('Chromium'):
                chromium = 1
            else:
                chromium = 0

            data['sulfurContent'] = request.POST.get('SulfurContent')
            data['heatTreatment'] = request.POST.get('heatTreatment')

            if request.POST.get('MGTEHTHA'):
                materialHTHA = 1
            else:
                materialHTHA = 0

            data['HTHAMaterialGrade'] = request.POST.get('HTHAMaterialGrade')

            if request.POST.get('MaterialPTA'):
                materialPTA = 1
            else:
                materialPTA = 0

            data['PTAMaterialGrade'] = request.POST.get('PTAMaterialGrade')
            data['materialCostFactor'] = request.POST.get('MaterialCostFactor')
            # Coating, Clading
            if request.POST.get('InternalCoating'):
                InternalCoating = 1
            else:
                InternalCoating = 0

            if request.POST.get('ExternalCoating'):
                ExternalCoating = 1
            else:
                ExternalCoating = 0

            data['ExternalCoatingID'] = request.POST.get('ExternalCoatingID')
            data['ExternalCoatingQuality'] = request.POST.get('ExternalCoatingQuality')

            if request.POST.get('SCWD'):
                supportMaterial = 1
            else:
                supportMaterial = 0

            if request.POST.get('InternalCladding'):
                InternalCladding = 1
            else:
                InternalCladding = 0

            data['CladdingCorrosionRate'] = request.POST.get('CladdingCorrosionRate')
            data['claddingthickness'] = request.POST.get('CladdingThickness')

            if request.POST.get('InternalLining'):
                InternalLining = 1
            else:
                InternalLining = 0

            data['InternalLinerType'] = request.POST.get('InternalLinerType')
            data['InternalLinerCondition'] = request.POST.get('InternalLinerCondition')

            if request.POST.get('ExternalInsulation') == "on" or request.POST.get('ExternalInsulation') == 1:
                ExternalInsulation = 1
            else:
                ExternalInsulation = 0

            if request.POST.get('ICC'):
                InsulationCholride = 1
            else:
                InsulationCholride = 0

            data['ExternalInsulationType'] = request.POST.get('ExternalInsulationType')
            data['InsulationCondition'] = request.POST.get('InsulationCondition')
            # Steam
            data['NaOHConcentration'] = request.POST.get('NaOHConcentration')
            data['ReleasePercentToxic'] = request.POST.get('RFPT')
            data['ChlorideIon'] = request.POST.get('ChlorideIon')
            data['CO3'] = request.POST.get('CO3')
            data['H2SContent'] = request.POST.get('H2SContent')
            data['PHWater'] = request.POST.get('PHWater')

            if request.POST.get('EAGTA'):
                exposureAcid = 1
            else:
                exposureAcid = 0

            if request.POST.get('ToxicConstituents'):
                ToxicConstituents = 1
            else:
                ToxicConstituents = 0

            data['ExposureAmine'] = request.POST.get('ExposureAmine')
            data['AminSolution'] = request.POST.get('ASC')

            if request.POST.get('APDO'):
                aquaDuringOP = 1
            else:
                aquaDuringOP = 0

            if request.POST.get('APDSD'):
                aquaDuringShutdown = 1
            else:
                aquaDuringShutdown = 0

            if request.POST.get('EnvironmentCH2S'):
                EnvironmentCH2S = 1
            else:
                EnvironmentCH2S = 0

            if request.POST.get('PHA'):
                presentHF = 1
            else:
                presentHF = 0

            if request.POST.get('PresenceCyanides'):
                presentCyanide = 1
            else:
                presentCyanide = 0

            if request.POST.get('PCH'):
                processHydrogen = 1
            else:
                processHydrogen = 0

            if request.POST.get('ECCAC'):
                environCaustic = 1
            else:
                environCaustic = 0

            if request.POST.get('ESBC'):
                exposedSulfur = 1
            else:
                exposedSulfur = 0

            if request.POST.get('MEFMSCC'):
                materialExposedFluid = 1
            else:
                materialExposedFluid = 0

            if request.POST.get('EToAcid'):
                etoacid = 1
            else:
                etoacid = 0

            # CA
            data['APIFluid'] = request.POST.get('APIFluid')
            data['MassInventory'] = request.POST.get('MassInventory')
            data['Systerm'] = request.POST.get('Systerm')
            data['ToxicFluid'] = request.POST.get('ToxicFluid')
            data['ToxicFluidPercent'] = request.POST.get('ToxicFluidPercent')
            data['PhaseStorage'] = request.POST.get('phaseOfFluid')
            data['LiquidLevel'] = request.POST.get('LiquidLevel')
            data['MassComponent'] = request.POST.get('MassComponent')
            data['EquipmentCost'] = request.POST.get('EquipmentCost')
            data['MittigationSystem'] = request.POST.get('MittigationSystem')
            data['ProductionCost'] = request.POST.get('ProductionCost')
            data['ToxicPercent'] = request.POST.get('ToxicPercent')
            data['InjureCost'] = request.POST.get('InjureCost')
            data['ReleaseDuration'] = request.POST.get('ReleaseDuration')
            data['EnvironmentCost'] = request.POST.get('EnvironmentCost')
            data['PersonDensity'] = request.POST.get('PersonDensity')
            data['ProcessUnit'] = request.POST.get('ProcessUnit')
            data['OutageMulti'] = request.POST.get('OutageMulti')
            if request.POST.get(
                    'DetectionType') == "Intrumentation designed specifically to detect material losses by changes in operating conditions (i.e loss of pressure or flow) in the system":
                detectiontype = 'A'
            elif request.POST.get(
                    'DetectionType') == "Suitably located detectors to determine when the material is present outside the pressure-containing envelope":
                detectiontype = 'B'
            else:
                detectiontype = 'C'
            data['DetectionType'] = detectiontype
            if request.POST.get(
                    'IsolationType') == "Isolation or shutdown systerms activated directly from process instrumentation or detectors, with no operator intervention":
                isolationtype = 'A'
            elif request.POST.get(
                    'IsolationType') == "Isolation or shutdown systems activated by operators in the control room or other suitable locations remote from the leak":
                isolationtype = 'B'
            else:
                isolationtype = 'C'
            data['IsolationType'] = isolationtype

            rwassessment.assessmentdate = data['assessmentdate']
            rwassessment.proposalname = data['assessmentname']
            rwassessment.save()

            rwequipment.adminupsetmanagement = adminControlUpset
            rwequipment.containsdeadlegs = containsDeadlegs
            rwequipment.cyclicoperation = cylicOP
            rwequipment.highlydeadleginsp = HighlyEffe
            rwequipment.downtimeprotectionused = downtime
            rwequipment.externalenvironment = data['ExternalEnvironment']
            rwequipment.heattraced = heatTrace
            rwequipment.interfacesoilwater = interfaceSoilWater
            rwequipment.lineronlinemonitoring = linerOnlineMoniter
            rwequipment.materialexposedtoclext = materialExposed
            rwequipment.minreqtemperaturepressurisation = data['minTemp']
            rwequipment.onlinemonitoring = data['OnlineMonitoring']
            rwequipment.presencesulphideso2 = presentSulphide
            rwequipment.presencesulphideso2shutdown = presentSulphidesShutdown
            rwequipment.pressurisationcontrolled = pressureControl
            rwequipment.pwht = pwht
            rwequipment.steamoutwaterflush = steamOut
            rwequipment.thermalhistory = data['ThermalHistory']
            rwequipment.yearlowestexptemp = lowestTemp
            rwequipment.volume = data['EquipmentVolumn']
            rwequipment.save()

            rwcomponent.nominaldiameter = data['normaldiameter']
            rwcomponent.nominalthickness = data['normalthick']
            rwcomponent.currentthickness = data['currentthick']
            rwcomponent.minreqthickness = data['tmin']
            rwcomponent.currentcorrosionrate = data['currentrate']
            rwcomponent.weldjointefficiency = data['weldjointeff']
            rwcomponent.branchdiameter = data['branchDiameter']
            rwcomponent.branchjointtype = data['joinTypeBranch']
            rwcomponent.brinnelhardness = data['MaxBrinell']
            rwcomponent.deltafatt = data['deltafatt']
            rwcomponent.chemicalinjection = chemicalInj
            rwcomponent.highlyinjectioninsp = HFICI
            rwcomponent.complexityprotrusion = data['complex']
            rwcomponent.correctiveaction = data['correctActionMitigate']
            rwcomponent.crackspresent = crackpresent
            rwcomponent.cyclicloadingwitin15_25m = data['CylicLoad']
            rwcomponent.damagefoundinspection = damageDuringInsp
            rwcomponent.structuralthickness = data['structuralthickness']
            rwcomponent.hthadamage = hthadamage
            rwcomponent.minstructuralthickness = minstruc
            rwcomponent.numberpipefittings = data['numberPipe']
            rwcomponent.pipecondition = data['pipeCondition']
            rwcomponent.previousfailures = data['prevFailure']
            rwcomponent.shakingamount = data['shakingPipe']
            rwcomponent.shakingdetected = visibleSharkingProtect
            rwcomponent.shakingtime = data['timeShakingPipe']
            rwcomponent.allowablestress = data['allowStress']
            rwcomponent.fabricatedsteel = p1andp3
            rwcomponent.equipmentsatisfied = equipmentrequire
            rwcomponent.nominaloperatingconditions = operatingcondition
            rwcomponent.cetgreaterorequal = cet
            rwcomponent.cyclicservice = cyclicservice
            rwcomponent.equipmentcircuitshock = equipmentorCircuit
            # rwcomponent.trampelements=TrampElement
            rwcomponent.brittlefracturethickness = data['BrittleFacture']
            rwcomponent.componentvolume = data['compvolume']
            rwcomponent.save()

            rwstream.aminesolution = data['AminSolution']
            rwstream.aqueousoperation = aquaDuringOP
            rwstream.aqueousshutdown = aquaDuringShutdown
            rwstream.toxicconstituent = ToxicConstituents
            rwstream.caustic = environCaustic
            rwstream.chloride = data['ChlorideIon']
            rwstream.co3concentration = data['CO3']
            rwstream.cyanide = presentCyanide
            rwstream.exposedtogasamine = exposureAcid
            rwstream.exposedtosulphur = exposedSulfur
            rwstream.exposuretoamine = data['ExposureAmine']
            rwstream.h2s = EnvironmentCH2S
            rwstream.h2sinwater = data['H2SContent']
            rwstream.hydrogen = processHydrogen
            rwstream.hydrofluoric = presentHF
            rwstream.materialexposedtoclint = materialExposedFluid
            rwstream.maxoperatingpressure = data['maxOP']
            rwstream.maxoperatingtemperature = float(data['maxOT'])
            rwstream.minoperatingpressure = float(data['minOP'])
            rwstream.minoperatingtemperature = data['minOT']
            rwstream.criticalexposuretemperature = data['criticalTemp']
            rwstream.naohconcentration = data['NaOHConcentration']
            rwstream.releasefluidpercenttoxic = float(data['ReleasePercentToxic'])
            rwstream.waterph = float(data['PHWater'])
            rwstream.h2spartialpressure = float(data['OpHydroPressure'])
            rwstream.storagephase = data['PhaseStorage']
            rwstream.liquidlevel = float(data['LiquidLevel'])
            rwstream.save()

            rwexcor.minus12tominus8 = data['OP1']
            rwexcor.minus8toplus6 = data['OP2']
            rwexcor.plus6toplus32 = data['OP3']
            rwexcor.plus32toplus71 = data['OP4']
            rwexcor.plus71toplus107 = data['OP5']
            rwexcor.plus107toplus121 = data['OP6']
            rwexcor.plus121toplus135 = data['OP7']
            rwexcor.plus135toplus162 = data['OP8']
            rwexcor.plus162toplus176 = data['OP9']
            rwexcor.morethanplus176 = data['OP10']
            rwexcor.save()

            rwcoat.externalcoating = ExternalCoating
            rwcoat.externalinsulation = ExternalInsulation
            rwcoat.internalcladding = InternalCladding
            rwcoat.internalcoating = InternalCoating
            rwcoat.internallining = InternalLining
            rwcoat.externalcoatingdate = data['ExternalCoatingID']
            rwcoat.externalcoatingquality = data['ExternalCoatingQuality']
            rwcoat.externalinsulationtype = data['ExternalInsulationType']
            rwcoat.insulationcondition = data['InsulationCondition']
            rwcoat.insulationcontainschloride = InsulationCholride
            rwcoat.internallinercondition = data['InternalLinerCondition']
            rwcoat.internallinertype = data['InternalLinerType']
            rwcoat.claddingcorrosionrate = data['CladdingCorrosionRate']
            rwcoat.claddingthickness = data['claddingthickness']
            rwcoat.supportconfignotallowcoatingmaint = supportMaterial
            rwcoat.save()

            rwmaterial.corrosionallowance = data['CA']
            rwmaterial.materialname = data['material']
            rwmaterial.designpressure = data['designPressure']
            rwmaterial.designtemperature = data['maxDesignTemp']
            rwmaterial.mindesigntemperature = data['minDesignTemp']
            rwmaterial.sigmaphase = data['sigmaPhase']
            rwmaterial.sulfurcontent = data['sulfurContent']
            rwmaterial.heattreatment = data['heatTreatment']
            rwmaterial.referencetemperature = data['tempRef']
            rwmaterial.ptamaterialcode = data['PTAMaterialGrade']
            rwmaterial.hthamaterialcode = data['HTHAMaterialGrade']
            rwmaterial.ispta = materialPTA
            rwmaterial.ishtha = materialHTHA
            rwmaterial.austenitic = austeniticStell
            rwmaterial.temper = suscepTemp
            rwmaterial.carbonlowalloy = cacbonAlloy
            rwmaterial.nickelbased = nickelAlloy
            rwmaterial.chromemoreequal12 = chromium
            rwmaterial.costfactor = data['materialCostFactor']
            rwmaterial.yieldstrength = data['yieldstrength']
            rwmaterial.tensilestrength = data['tensilestrength']
            rwmaterial.save()

            rwinputca.api_fluid = data['APIFluid']
            rwinputca.system = data['Systerm']
            rwinputca.release_duration = data['ReleaseDuration']
            rwinputca.detection_type = data['DetectionType']
            rwinputca.isulation_type = data['IsolationType']
            rwinputca.mitigation_system = data['MittigationSystem']
            rwinputca.equipment_cost = data['EquipmentCost']
            rwinputca.injure_cost = data['InjureCost']
            rwinputca.evironment_cost = data['EnvironmentCost']
            rwinputca.toxic_percent = data['ToxicPercent']
            rwinputca.personal_density = data['PersonDensity']
            rwinputca.material_cost = data['materialCostFactor']
            rwinputca.production_cost = data['ProductionCost']
            rwinputca.mass_inventory = data['MassInventory']
            rwinputca.mass_component = data['MassComponent']
            rwinputca.stored_pressure = float(data['minOP']) * 6.895
            rwinputca.stored_temp = data['minOT']
            rwinputca.toxic_fluid = data['ToxicFluid']
            rwinputca.toxic_percent = data['ToxicFluidPercent']
            rwinputca.process_unit = data['ProcessUnit']
            rwinputca.outage_multiplier = data['OutageMulti']
            rwinputca.save()

            # Customize code here
            ReCalculate.ReCalculate(proposalID)
            return redirect('damgeFactor', proposalID=proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/proposal/proposalNormalEdit.html',
                  {'page': 'editProposal', 'api': Fluid, 'rwAss': rwassessment, 'rwEq': rwequipment,
                   'rwComp': rwcomponent, 'rwStream': rwstream, 'rwExcot': rwexcor,
                   'rwCoat': rwcoat, 'rwMaterial': rwmaterial, 'rwInputCa': rwinputca,
                   'assDate': assDate, 'extDate': extDate,
                   'componentID': rwassessment.componentid_id,
                   'equipmentID': rwassessment.equipmentid_id, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count, 'toxicfluid': ToxicFluid})


def EditTank(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwassessment = models.RwAssessment.objects.get(id=proposalID)
        rwequipment = models.RwEquipment.objects.get(id=proposalID)
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwstream = models.RwStream.objects.get(id=proposalID)
        rwexcor = models.RwExtcorTemperature.objects.get(id=proposalID)
        rwcoat = models.RwCoating.objects.get(id=proposalID)
        rwmaterial = models.RwMaterial.objects.get(id=proposalID)
        rwinputca = models.RwInputCaTank.objects.get(id=proposalID)
        assDate = rwassessment.assessmentdate.strftime('%Y-%m-%d')
        try:
            extDate = rwcoat.externalcoatingdate.strftime('%Y-%m-%d')
        except:
            extDate = datetime.now().strftime('%Y-%m-%d')

        comp = models.ComponentMaster.objects.get(componentid=rwassessment.componentid_id)
        eq = models.EquipmentMaster.objects.get(equipmentid=rwassessment.equipmentid_id)
        datafaci = models.Facility.objects.get(facilityid=eq.facilityid_id)
        data = {}
        isshell = False
        if comp.componenttypeid_id == 9 or comp.componenttypeid_id == 13:  # tuansua
            isshell = True
        if request.method == 'POST':
            # Data Assessment
            data['confidencecr'] = request.POST.get('ConfidenceCR')  # bo sung level of confident for tankbottom
            data['assessmentName'] = request.POST.get('AssessmentName')
            data['assessmentdate'] = request.POST.get('assessmentdate')
            data['riskperiod'] = request.POST.get('RiskAnalysisPeriod')
            data['assessmentmethod'] = request.POST.get('AssessmentMethod')
            data['apicomponenttypeid'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
            data['equipmenttype'] = models.EquipmentType.objects.get(
                equipmenttypeid=eq.equipmenttypeid_id).equipmenttypename
            # Data Equipment Properties
            if request.POST.get('Admin'):
                adminControlUpset = 1
            else:
                adminControlUpset = 0

            if request.POST.get('CylicOper'):
                cylicOp = 1
            else:
                cylicOp = 0

            if request.POST.get('Highly'):
                highlyDeadleg = 1
            else:
                highlyDeadleg = 0

            if request.POST.get('Steamed'):
                steamOutWater = 1
            else:
                steamOutWater = 0
            if request.POST.get('Downtime'):
                downtimeProtect = 1
            else:
                downtimeProtect = 0

            if request.POST.get('PWHT'):
                pwht = 1
            else:
                pwht = 0

            if request.POST.get('HeatTraced'):
                heatTrace = 1
            else:
                heatTrace = 0

            data['distance'] = request.POST.get('Distance')

            if request.POST.get('InterfaceSoilWater'):
                interfaceSoilWater = 1
            else:
                interfaceSoilWater = 0

            data['soiltype'] = request.POST.get('typeofSoil')

            if request.POST.get('PressurisationControlled'):
                pressureControl = 1
            else:
                pressureControl = 0

            data['minRequireTemp'] = request.POST.get('MinReq')

            if request.POST.get('lowestTemp'):
                lowestTemp = 1
            else:
                lowestTemp = 0

            if request.POST.get('MFTF'):
                materialChlorineExt = 1
            else:
                materialChlorineExt = 0

            if request.POST.get('LOM'):
                linerOnlineMonitor = 1
            else:
                linerOnlineMonitor = 0

            if request.POST.get('PresenceofSulphides'):
                presenceSulphideOP = 1
            else:
                presenceSulphideOP = 0

            if request.POST.get('PresenceofSulphidesShutdow'):
                presenceSulphideShut = 1
            else:
                presenceSulphideShut = 0

            if request.POST.get('ComponentWelded'):
                componentWelded = 1
            else:
                componentWelded = 0

            if request.POST.get('TMA'):
                tankIsMaintain = 1
            else:
                tankIsMaintain = 0

            data['adjustSettlement'] = request.POST.get('AdjForSettlement')
            data['extEnvironment'] = request.POST.get('ExternalEnvironment')
            data['EnvSensitivity'] = request.POST.get('EnvironmentSensitivity')
            data['themalHistory'] = request.POST.get('ThermalHistory')
            data['onlineMonitor'] = request.POST.get('OnlineMonitoring')
            data['equipmentVolumn'] = request.POST.get('EquipmentVolume')
            # Component Properties
            data['structuralthickness'] = request.POST.get('StructuralThickness')
            data['tankDiameter'] = request.POST.get('TankDiameter')
            data['NominalThickness'] = request.POST.get('NominalThickness')
            data['currentThick'] = request.POST.get('CurrentThickness')
            data['minRequireThick'] = request.POST.get('MinReqThick')
            data['currentCorrosion'] = request.POST.get('CurrentCorrosionRate')
            data['HeightEShellC'] = request.POST.get('HeightEShellC')
            data['ComponentVolume'] = request.POST.get('CompVolume')
            data['WeldJointeff'] = request.POST.get('WeldJointEff')
            if request.POST.get('MinStructural'):
                minstruc = 1
            else:
                minstruc = 0
            if request.POST.get('DFDI'):
                damageFound = 1
            else:
                damageFound = 0

            if request.POST.get('PresenceCracks'):
                crackPresence = 1
            else:
                crackPresence = 0

            if request.POST.get('TrampElements'):
                trampElements = 1
            else:
                trampElements = 0

            if request.POST.get('ReleasePreventionBarrier'):
                preventBarrier = 1
            else:
                preventBarrier = 0

            if request.POST.get('ConcreteFoundation'):
                concreteFoundation = 1
            else:
                concreteFoundation = 0

            if request.POST.get('P1AndP3'):
                p1andp3 = 1
            else:
                p1andp3 = 0

            if request.POST.get('EquipmentRequirements'):
                equipmentrequire = 1
            else:
                equipmentrequire = 0

            if request.POST.get('OperatingConditions'):
                operatingcondition = 1
            else:
                operatingcondition = 0

            if request.POST.get('CETtheMAWP'):
                cet = 1
            else:
                cet = 0

            if request.POST.get('CyclicService'):
                cyclicservice = 1
            else:
                cyclicservice = 0

            if request.POST.get('EquipmentorCircuit'):
                equipmentorCircuit = 1
            else:
                equipmentorCircuit = 0

            data['maxBrinnelHardness'] = request.POST.get('MBHW')
            data['complexProtrusion'] = request.POST.get('ComplexityProtrusions')
            data['severityVibration'] = request.POST.get('SeverityVibration')

            # Operating condition
            data['maxOT'] = request.POST.get('MaxOT')
            data['maxOP'] = request.POST.get('MaxOP')
            data['minOT'] = request.POST.get('MinOT')
            data['minOP'] = request.POST.get('MinOP')
            data['H2Spressure'] = request.POST.get('OHPP')
            data['criticalTemp'] = request.POST.get('CET')
            data['flowrate'] = request.POST.get('FlowRate')
            data['OP1'] = request.POST.get('Operating1')
            data['OP2'] = request.POST.get('Operating2')
            data['OP3'] = request.POST.get('Operating3')
            data['OP4'] = request.POST.get('Operating4')
            data['OP5'] = request.POST.get('Operating5')
            data['OP6'] = request.POST.get('Operating6')
            data['OP7'] = request.POST.get('Operating7')
            data['OP8'] = request.POST.get('Operating8')
            data['OP9'] = request.POST.get('Operating9')
            data['OP10'] = request.POST.get('Operating10')

            # Material
            data['materialName'] = request.POST.get('materialname')
            data['maxDesignTemp'] = request.POST.get('MaxDesignTemp')
            data['minDesignTemp'] = request.POST.get('MinDesignTemp')
            data['designPressure'] = request.POST.get('DesignPressure')
            data['refTemp'] = request.POST.get('ReferenceTemperature')
            data['allowStress'] = request.POST.get('ASAT')
            data['brittleThick'] = request.POST.get('BFGT')
            data['corrosionAllow'] = request.POST.get('CorrosionAllowance')
            data['yieldstrength'] = request.POST.get('YieldStrength')
            data['tensilestrength'] = request.POST.get('TensileStrength')
            if request.POST.get('CoLAS'):
                carbonLowAlloySteel = 1
            else:
                carbonLowAlloySteel = 0

            if request.POST.get('AusteniticSteel'):
                austeniticSteel = 1
            else:
                austeniticSteel = 0

            if request.POST.get('NickelAlloy'):
                nickelAlloy = 1
            else:
                nickelAlloy = 0

            if request.POST.get('Chromium'):
                chromium = 1
            else:
                chromium = 0

            data['sulfurContent'] = request.POST.get('SulfurContent')
            data['heatTreatment'] = request.POST.get('heatTreatment')

            if request.POST.get('MGTEPTA'):
                materialPTA = 1
            else:
                materialPTA = 0

            data['PTAMaterialGrade'] = request.POST.get('PTAMaterialGrade')
            data['materialCostFactor'] = request.POST.get('MaterialCostFactor')
            data['productionCost'] = request.POST.get('ProductionCost')

            # Coating, Cladding
            if request.POST.get('InternalCoating'):
                internalCoating = 1
            else:
                internalCoating = 0

            if request.POST.get('ExternalCoating'):
                externalCoating = 1
            else:
                externalCoating = 0

            data['externalInstallDate'] = request.POST.get('ExternalCoatingID')
            data['externalCoatQuality'] = request.POST.get('ExternalCoatingQuality')

            if request.POST.get('SCWD'):
                supportCoatingMaintain = 1
            else:
                supportCoatingMaintain = 0

            if request.POST.get('InternalCladding'):
                internalCladding = 1
            else:
                internalCladding = 0
            data['CladdingThinkness'] = request.POST.get('CladdingThinkness')
            data['cladCorrosion'] = request.POST.get('CladdingCorrosionRate')

            if request.POST.get('InternalLining'):
                internalLinning = 1
            else:
                internalLinning = 0

            data['internalLinnerType'] = request.POST.get('InternalLinerType')
            data['internalLinnerCondition'] = request.POST.get('InternalLinerCondition')

            if request.POST.get('ExternalInsulation'):
                extInsulation = 1
            else:
                extInsulation = 0

            if request.POST.get('ICC'):
                InsulationContainChloride = 1
            else:
                InsulationContainChloride = 0

            data['extInsulationType'] = request.POST.get('ExternalInsulationType')
            data['insulationCondition'] = request.POST.get('InsulationCondition')
            # Stream
            data['fluid'] = request.POST.get('Fluid')
            data['fluidHeight'] = request.POST.get('FluidHeight')
            data['fluidLeaveDike'] = request.POST.get('PFLD')
            data['fluidOnsite'] = request.POST.get('PFLDRS')
            data['fluidOffsite'] = request.POST.get('PFLDGoffsite')
            data['naohConcent'] = request.POST.get('NaOHConcentration')
            data['releasePercentToxic'] = request.POST.get('RFPT')
            data['chlorideIon'] = request.POST.get('ChlorideIon')
            data['co3'] = request.POST.get('CO3')
            data['h2sContent'] = request.POST.get('H2SContent')
            data['PHWater'] = request.POST.get('PHWater')

            if request.POST.get('EAGTA'):
                exposedAmine = 1
            else:
                exposedAmine = 0

            data['amineSolution'] = request.POST.get('AmineSolution')
            data['exposureAmine'] = request.POST.get('ExposureAmine')

            if request.POST.get('APDO'):
                aqueosOP = 1
            else:
                aqueosOP = 0

            if request.POST.get('EnvironmentCH2S'):
                environtH2S = 1
            else:
                environtH2S = 0

            if request.POST.get('APDSD'):
                aqueosShut = 1
            else:
                aqueosShut = 0

            if request.POST.get('PresenceCyanides'):
                cyanidesPresence = 1
            else:
                cyanidesPresence = 0

            if request.POST.get('presenceHF'):
                presentHF = 1
            else:
                presentHF = 0

            if request.POST.get('ECCAC'):
                environtCaustic = 1
            else:
                environtCaustic = 0

            if request.POST.get('PCH'):
                processContainHydro = 1
            else:
                processContainHydro = 0

            if request.POST.get('MEFMSCC'):
                materialChlorineIntern = 1
            else:
                materialChlorineIntern = 0

            if request.POST.get('ESBC'):
                exposedSulfur = 1
            else:
                exposedSulfur = 0

            if str(data['fluid']) == "Gasoline":
                apiFluid = "C6-C8"
            elif str(data['fluid']) == "Light Diesel Oil":
                apiFluid = "C9-C12"
            elif str(data['fluid']) == "Heavy Diesel Oil":
                apiFluid = "C13-C16"
            elif str(data['fluid']) == "Fuel Oil" or str(data['fluid']) == "Crude Oil":
                apiFluid = "C17-C25"
            else:
                apiFluid = "C25+"
            rwassessment.assessmentdate = data['assessmentdate']
            rwassessment.proposalname = data['assessmentName']
            rwassessment.assessmentmethod = data['assessmentmethod']
            rwassessment.save()
            # print("4")
            rwequipment.adminupsetmanagement = adminControlUpset
            rwequipment.cyclicoperation = cylicOp
            rwequipment.highlydeadleginsp = highlyDeadleg
            rwequipment.downtimeprotectionused = downtimeProtect
            rwequipment.steamoutwaterflush = steamOutWater
            rwequipment.pwht = pwht
            rwequipment.heattraced = heatTrace
            rwequipment.distancetogroundwater = data['distance']
            rwequipment.interfacesoilwater = interfaceSoilWater
            rwequipment.typeofsoil = data['soiltype']
            rwequipment.pressurisationcontrolled = pressureControl
            rwequipment.minreqtemperaturepressurisation = data['minRequireTemp']
            rwequipment.yearlowestexptemp = lowestTemp
            rwequipment.materialexposedtoclext = materialChlorineExt
            rwequipment.lineronlinemonitoring = linerOnlineMonitor
            rwequipment.presencesulphideso2 = presenceSulphideOP
            rwequipment.presencesulphideso2shutdown = presenceSulphideShut
            rwequipment.componentiswelded = componentWelded
            rwequipment.tankismaintained = tankIsMaintain
            rwequipment.adjustmentsettle = data['adjustSettlement']
            rwequipment.externalenvironment = data['extEnvironment']
            rwequipment.environmentsensitivity = data['EnvSensitivity']
            rwequipment.onlinemonitoring = data['onlineMonitor']
            rwequipment.thermalhistory = data['themalHistory']
            rwequipment.managementfactor = datafaci.managementfactor
            rwequipment.volume = data['equipmentVolumn']
            rwequipment.save()
            # print("5")
            rwcomponent.nominaldiameter = data['tankDiameter']
            rwcomponent.nominalthickness = data['NominalThickness']
            rwcomponent.currentthickness = data['currentThick']
            rwcomponent.minreqthickness = data['minRequireThick']
            rwcomponent.currentcorrosionrate = data['currentCorrosion']
            rwcomponent.shellheight = data['HeightEShellC']
            rwcomponent.damagefoundinspection = damageFound
            rwcomponent.crackspresent = crackPresence
            rwcomponent.componentvolume = data['ComponentVolume']
            rwcomponent.weldjointefficiency = data['WeldJointeff']
            # rwcomponent.trampelements=trampElements
            rwcomponent.structuralthickness = data['structuralthickness']
            rwcomponent.releasepreventionbarrier = preventBarrier
            rwcomponent.concretefoundation = concreteFoundation
            rwcomponent.brinnelhardness = data['maxBrinnelHardness']
            rwcomponent.complexityprotrusion = data['complexProtrusion']
            rwcomponent.severityofvibration = data['severityVibration']
            rwcomponent.allowablestress = data['allowStress']
            rwcomponent.brittlefracturethickness = data['brittleThick']
            rwcomponent.fabricatedsteel = p1andp3
            rwcomponent.equipmentsatisfied = equipmentrequire
            rwcomponent.nominaloperatingconditions = operatingcondition
            rwcomponent.cetgreaterorequal = cet
            rwcomponent.cyclicservice = cyclicservice
            rwcomponent.equipmentcircuitshock = equipmentorCircuit
            rwcomponent.minstructuralthickness = minstruc
            rwcomponent.save()
            # print("6")
            rwstream.maxoperatingtemperature = data['maxOT']
            rwstream.maxoperatingpressure = data['maxOP']
            rwstream.minoperatingtemperature = data['minOT']
            rwstream.minoperatingpressure = data['minOP']
            rwstream.h2spartialpressure = data['H2Spressure']
            rwstream.criticalexposuretemperature = data['criticalTemp']
            rwstream.flowrate = data['flowrate']
            rwstream.tankfluidname = data['fluid']
            rwstream.fluidheight = data['fluidHeight']
            rwstream.fluidleavedikepercent = data['fluidLeaveDike']
            rwstream.fluidleavedikeremainonsitepercent = data['fluidOnsite']
            rwstream.fluidgooffsitepercent = data['fluidOffsite']
            rwstream.naohconcentration = data['naohConcent']
            rwstream.releasefluidpercenttoxic = data['releasePercentToxic']
            rwstream.chloride = data['chlorideIon']
            rwstream.co3concentration = data['co3']
            rwstream.h2sinwater = data['h2sContent']
            rwstream.waterph = data['PHWater']
            rwstream.exposedtogasamine = exposedAmine
            rwstream.aminesolution = data['amineSolution']
            rwstream.exposuretoamine = data['exposureAmine']
            rwstream.aqueousoperation = aqueosOP
            rwstream.h2s = environtH2S
            rwstream.aqueousshutdown = aqueosShut
            rwstream.cyanide = cyanidesPresence
            rwstream.hydrofluoric = presentHF
            rwstream.caustic = environtCaustic
            rwstream.hydrogen = processContainHydro
            rwstream.materialexposedtoclint = materialChlorineIntern
            rwstream.exposedtosulphur = exposedSulfur
            rwstream.save()
            # print("7")
            rwexcor.minus12tominus8 = data['OP1']
            rwexcor.minus8toplus6 = data['OP2']
            rwexcor.plus6toplus32 = data['OP3']
            rwexcor.plus32toplus71 = data['OP4']
            rwexcor.plus71toplus107 = data['OP5']
            rwexcor.plus107toplus121 = data['OP6']
            rwexcor.plus121toplus135 = data['OP7']
            rwexcor.plus135toplus162 = data['OP8']
            rwexcor.plus162toplus176 = data['OP9']
            rwexcor.morethanplus176 = data['OP10']
            rwexcor.save()
            # print("8")

            rwcoat.internalcoating = internalCoating
            rwcoat.externalcoating = externalCoating
            rwcoat.externalcoatingdate = data['externalInstallDate']
            rwcoat.externalcoatingquality = data['externalCoatQuality']
            rwcoat.supportconfignotallowcoatingmaint = supportCoatingMaintain
            rwcoat.internalcladding = internalCladding
            rwcoat.claddingcorrosionrate = data['cladCorrosion']
            rwcoat.claddingthickness = data['CladdingThinkness']
            rwcoat.internallining = internalLinning
            rwcoat.internallinertype = data['internalLinnerType']
            rwcoat.internallinercondition = data['internalLinnerCondition']
            rwcoat.externalinsulation = extInsulation
            rwcoat.insulationcontainschloride = InsulationContainChloride
            rwcoat.externalinsulationtype = data['extInsulationType']
            rwcoat.insulationcondition = data['insulationCondition']
            rwcoat.save()

            # print("9")
            rwmaterial.materialname = data['materialName']
            rwmaterial.designtemperature = data['maxDesignTemp']
            rwmaterial.mindesigntemperature = data['minDesignTemp']
            rwmaterial.designpressure = data['designPressure']
            rwmaterial.referencetemperature = data['refTemp']
            rwmaterial.corrosionallowance = data['corrosionAllow']
            rwmaterial.carbonlowalloy = carbonLowAlloySteel
            rwmaterial.austenitic = austeniticSteel
            rwmaterial.nickelbased = nickelAlloy
            rwmaterial.chromemoreequal12 = chromium
            rwmaterial.sulfurcontent = data['sulfurContent']
            rwmaterial.heattreatment = data['heatTreatment']
            rwmaterial.ispta = materialPTA
            rwmaterial.ptamaterialcode = data['PTAMaterialGrade']
            rwmaterial.costfactor = data['materialCostFactor']
            rwmaterial.yieldstrength = data['yieldstrength']
            rwmaterial.tensilestrength = data['tensilestrength']
            rwmaterial.save()
            # print("10")
            rwinputca.fluid_height = data['fluidHeight']
            rwinputca.shell_course_height = data['HeightEShellC']
            rwinputca.tank_diametter = data['tankDiameter']
            rwinputca.prevention_barrier = preventBarrier
            rwinputca.environ_sensitivity = data['EnvSensitivity']
            rwinputca.p_lvdike = data['fluidLeaveDike']
            rwinputca.p_offsite = data['fluidOffsite']
            rwinputca.p_onsite = data['fluidOnsite']
            rwinputca.soil_type = data['soiltype']
            rwinputca.tank_fluid = data['fluid']
            rwinputca.api_fluid = apiFluid
            rwinputca.sw = data['distance']
            rwinputca.productioncost = data['productionCost']
            rwinputca.save()
            # print("ok")
            ReCalculate.ReCalculate(proposalID)
            return redirect('damgeFactor', proposalID=proposalID)
    except:
        raise Http404
    return render(request, 'FacilityUI/proposal/proposalTankEdit.html',
                  {'page': 'editProposal', 'isshell': isshell, 'rwAss': rwassessment,
                   'rwEq': rwequipment, 'rwComp': rwcomponent,
                   'rwStream': rwstream, 'rwExcot': rwexcor,
                   'rwCoat': rwcoat, 'rwMaterial': rwmaterial, 'rwInputCa': rwinputca,
                   'assDate': assDate, 'extDate': extDate,
                   'componentID': comp.componentid,
                   'equipmentID': comp.equipmentid_id, 'info': request.session, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def RiskMatrix(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        locatAPI1 = {}
        locatAPI2 = {}
        locatAPI3 = {}
        locatAPI1['x'] = 0
        locatAPI1['y'] = 500

        locatAPI2['x'] = 0
        locatAPI2['y'] = 500

        locatAPI3['x'] = 0
        locatAPI3['y'] = 500

        df = models.RwFullPof.objects.get(id=proposalID)
        ca = models.RwFullFcof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0

        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        Ca = round(ca.fcofvalue, 2)
        DF1 = round(df.totaldfap1, 2)
        DF2 = round(df.totaldfap2, 2)
        DF3 = round(df.totaldfap3, 2)
    except:
        raise Http404
    return render(request, 'FacilityUI/risk_summary/riskMatrix.html',
                  {'page': 'riskMatrix', 'API1': location.locat(df.totaldfap1, ca.fcofvalue),
                   'API2': location.locat(df.totaldfap2, ca.fcofvalue),
                   'API3': location.locat(df.totaldfap3, ca.fcofvalue), 'DF1': DF1, 'DF2': DF2, 'DF3': DF3, 'ca': Ca,
                   'ass': rwAss, 'isTank': isTank, 'isShell': isShell, 'df': df, 'proposalID': proposalID,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def FullyDamageFactor(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        df = models.RwFullPof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        data = {}
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        data['thinningType'] = df.thinningtype
        data['gfftotal'] = df.gfftotal
        data['fms'] = df.fms
        data['thinningap1'] = roundData.roundDF(df.thinningap1)
        data['thinningap2'] = roundData.roundDF(df.thinningap2)
        data['thinningap3'] = roundData.roundDF(df.thinningap3)
        data['sccap1'] = roundData.roundDF(df.sccap1)
        data['sccap2'] = roundData.roundDF(df.sccap2)
        data['sccap3'] = roundData.roundDF(df.sccap3)
        data['externalap1'] = roundData.roundDF(df.externalap1)
        data['externalap2'] = roundData.roundDF(df.externalap2)
        data['externalap3'] = roundData.roundDF(df.externalap3)
        data['htha_ap1'] = roundData.roundDF(df.htha_ap1)
        data['htha_ap2'] = roundData.roundDF(df.htha_ap2)
        data['htha_ap3'] = roundData.roundDF(df.htha_ap3)
        data['brittleap1'] = roundData.roundDF(df.brittleap1)
        data['brittleap2'] = roundData.roundDF(df.brittleap2)
        data['brittleap3'] = roundData.roundDF(df.brittleap3)
        data['fatigueap1'] = roundData.roundDF(df.fatigueap1)
        data['fatigueap2'] = roundData.roundDF(df.fatigueap2)
        data['fatigueap3'] = roundData.roundDF(df.fatigueap3)
        data['thinninggeneralap1'] = roundData.roundDF(df.thinninggeneralap1)
        data['thinninggeneralap2'] = roundData.roundDF(df.thinninggeneralap2)
        data['thinninggeneralap3'] = roundData.roundDF(df.thinninggeneralap3)
        data['thinninglocalap1'] = roundData.roundDF(df.thinninglocalap1)
        data['thinninglocalap2'] = roundData.roundDF(df.thinninglocalap2)
        data['thinninglocalap3'] = roundData.roundDF(df.thinninglocalap3)
        data['totaldfap1'] = roundData.roundDF(df.totaldfap1)
        data['totaldfap2'] = roundData.roundDF(df.totaldfap2)
        data['totaldfap3'] = roundData.roundDF(df.totaldfap3)
        data['pofap1'] = roundData.roundPoF(df.pofap1)
        data['pofap2'] = roundData.roundPoF(df.pofap2)
        data['pofap3'] = roundData.roundPoF(df.pofap3)
        data['pofap1category'] = df.pofap1category
        data['pofap2category'] = df.pofap2category
        data['pofap3category'] = df.pofap3category
        if '_show1' in request.POST:
            return redirect('thining', proposalID=proposalID)
        if '_show2' in request.POST:
            return redirect('governing', proposalID=proposalID)
        if request.method == 'POST':
            df.thinningtype = request.POST.get('thinningType')
            df.save()
            ReCalculate.ReCalculate(proposalID)
            return redirect('damgeFactor', proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/risk_summary/dfFull.html',
                  {'page': 'damageFactor', 'obj': data, 'assess': rwAss, 'isTank': isTank,
                   'isShell': isShell, 'proposalID': proposalID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def ShowThining(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        data = []
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwassessment = models.RwAssessment.objects.get(id=proposalID)
        rwcoat = models.RwCoating.objects.get(id=proposalID)
        rwmaterial = models.RwMaterial.objects.get(id=proposalID)
        rwequipment = models.RwEquipment.objects.get(id=proposalID)
        # damageMachinsm = models.RwDamageMechanism.objects.get(id_dm=proposalID)
        obj = {}
        obj['AllowableStress'] = rwcomponent.allowablestress
        obj['MinimunRequiredThickness'] = rwcomponent.minreqthickness
        obj['WeltJointEfficiency'] = rwcomponent.weldjointefficiency
        obj['CorrosionRate'] = rwcomponent.currentcorrosionrate
        obj['Diameter'] = rwcomponent.nominaldiameter
        obj['NominalThickness'] = rwcomponent.nominalthickness
        obj['CurentThickness'] = rwcomponent.currentthickness
        obj['ChemicalInjection'] = rwcomponent.chemicalinjection
        obj['HighlyEffectiveInspectionforChemicalInjection'] = rwcomponent.highlyinjectioninsp
        obj['assessmentDate'] = rwassessment.assessmentdate
        obj['InternalCladding'] = rwcoat.internalcladding
        obj['CladdingCorrosionRate'] = rwcoat.claddingcorrosionrate
        obj['YeildStrength'] = rwmaterial.yieldstrength
        obj['TensileStrength'] = rwmaterial.tensilestrength
        obj['DesignPressure'] = rwmaterial.designpressure
        obj['Onlinemonitoring'] = rwequipment.onlinemonitoring
        obj['HighEffectiveDeadlegs'] = rwequipment.highlydeadleginsp
        # obj['LastInspectionDate'] = damageMachinsm.lastinspdate
        # obj['NumberofInspection'] = damageMachinsm.numberofinspections
        obj['LastInspectionDate'] = 0
        obj['NumberofInspection'] = 0
        data.append(obj)
        return render(request, 'FacilityUI/risk_summary/showThining.html',
                      {'page': 'thining', 'proposalID': proposalID, 'data': data, 'info': request.session, 'noti': noti,
                       'countnoti': countnoti, 'count': count})
    except Exception as e:
        print(e)
        raise Http404


def ShowGoverning(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'FacilityUI/risk_summary/showGoverning.html',
                  {'page': 'governing', 'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count})


def FullyConsequence(request, proposalID):  # Finance cof
    data = {}
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        rwstream = models.RwStream.objects.get(id=proposalID)
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 9 or component.componenttypeid_id == 13:
            isShell = 1
        else:
            isShell = 0
        if isBottom:
            bottomConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['hydraulic_water'] = roundData.roundFC(bottomConsequences.hydraulic_water)
            data['hydraulic_fluid'] = roundData.roundFC(bottomConsequences.hydraulic_fluid)
            data['seepage_velocity'] = roundData.roundFC(bottomConsequences.seepage_velocity)
            data['flow_rate_d1'] = roundData.roundFC(bottomConsequences.flow_rate_d1)
            data['flow_rate_d4'] = roundData.roundFC(bottomConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(bottomConsequences.leak_duration_d1)
            data['leak_duration_d4'] = roundData.roundFC(bottomConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(bottomConsequences.release_volume_leak_d1)
            data['release_volume_leak_d4'] = roundData.roundFC(bottomConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(bottomConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(bottomConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(bottomConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(bottomConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(bottomConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(bottomConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(bottomConsequences.fc_environ)
            data['material_factor'] = bottomConsequences.material_factor
            data['component_damage_cost'] = roundData.roundMoney(bottomConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(bottomConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(bottomConsequences.consequence)
            data['consequencecategory'] = bottomConsequences.consequencecategory
            return render(request, 'FacilityUI/risk_summary/fullyBottomConsequence.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count,
                           'isTank': isBottom,
                           'isShell': isShell})
        elif isShell:
            shellConsequences = models.RwCaTank.objects.get(id=proposalID)
            rwfullcoftank = models.RWFullCofTank.objects.filter(id=proposalID)
            data['hydraulic_water'] = roundData.roundFC(shellConsequences.hydraulic_water)  # tuansua
            data['hydraulic_fluid'] = roundData.roundFC(shellConsequences.hydraulic_fluid)  # tuansua
            data['seepage_velocity'] = roundData.roundFC(shellConsequences.seepage_velocity)  # tuansua
            data['flow_rate_d1'] = roundData.roundFC(shellConsequences.flow_rate_d1)
            data['flow_rate_d2'] = roundData.roundFC(shellConsequences.flow_rate_d2)
            data['flow_rate_d3'] = roundData.roundFC(shellConsequences.flow_rate_d3)
            data['flow_rate_d4'] = roundData.roundFC(shellConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(shellConsequences.leak_duration_d1)
            data['leak_duration_d2'] = roundData.roundFC(shellConsequences.leak_duration_d2)
            data['leak_duration_d3'] = roundData.roundFC(shellConsequences.leak_duration_d3)
            data['leak_duration_d4'] = roundData.roundFC(shellConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(shellConsequences.release_volume_leak_d1)
            data['release_volume_leak_d2'] = roundData.roundFC(shellConsequences.release_volume_leak_d2)
            data['release_volume_leak_d3'] = roundData.roundFC(shellConsequences.release_volume_leak_d3)
            data['release_volume_leak_d4'] = roundData.roundFC(shellConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(shellConsequences.release_volume_rupture)
            data['liquid_height'] = roundData.roundFC(shellConsequences.liquid_height)
            data['volume_fluid'] = roundData.roundFC(shellConsequences.volume_fluid)
            data['time_leak_ground'] = roundData.roundFC(shellConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(shellConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(shellConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(shellConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(shellConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(shellConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(shellConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(shellConsequences.fc_environ)
            data['component_damage_cost'] = roundData.roundMoney(shellConsequences.component_damage_cost)
            data['damage_surrounding_equipment_cost'] = roundData.roundMoney(
                shellConsequences.damage_surrounding_equipment_cost)
            data['business_cost'] = roundData.roundMoney(shellConsequences.business_cost)
            data['associated_personnel_injury_cost'] = roundData.roundMoney(
                shellConsequences.associated_personnel_injury_cost)
            data['consequence'] = roundData.roundMoney(shellConsequences.consequence)
            data['consequencecategory'] = shellConsequences.consequencecategory
            # tuansua
            data['material_factor'] = shellConsequences.material_factor
            data['barrel_dike_leak'] = roundData.roundFC(shellConsequences.barrel_dike_leak)
            data['barrel_onsite_leak'] = roundData.roundFC(shellConsequences.barrel_onsite_leak)
            data['barrel_offsite_leak'] = roundData.roundFC(shellConsequences.barrel_offsite_leak)
            data['barrel_water_leak'] = roundData.roundFC(shellConsequences.barrel_water_leak)
            data['fc_environ_leak'] = roundData.roundFC(shellConsequences.fc_environ_leak)
            # bổ sung hiển thị 5 giá trị đầu vào và 3 kết quả đầu ra
            if rwfullcoftank.count() == 0:
                data['equip_cost'] = 0
                data['equip_outage_multiplier'] = 0
                data['prod_cost'] = 0
                data['pop_dens'] = 0
                data['inj_cost'] = 0
            else:
                rwfullcoftank = models.RWFullCofTank.objects.get(id=proposalID)
                data['equip_cost'] = rwfullcoftank.equipcost
                data['equip_outage_multiplier'] = rwfullcoftank.equipoutagemultiplier
                data['prod_cost'] = rwfullcoftank.prodcost
                data['pop_dens'] = rwfullcoftank.popdens
                data['inj_cost'] = rwfullcoftank.injcost
            # bo sung 5 tham số đầu vào
            if '_calculate' in request.POST:
                if request.method == 'POST':
                    data['equip_cost'] = request.POST.get('EquipCost')
                    data['equip_outage_multiplier'] = request.POST.get('EquipOutageMultiplier')
                    data['prod_cost'] = request.POST.get('ProdCost')
                    data['pop_dens'] = request.POST.get('PopDens')
                    data['inj_cost'] = request.POST.get('InjCost')
                    rwfullcoftank = models.RWFullCofTank(id=rwAss, equipcost=data['equip_cost'],
                                                         prodcost=data['prod_cost'],
                                                         equipoutagemultiplier=data['equip_outage_multiplier'],
                                                         popdens=data['pop_dens'], injcost=data['inj_cost'])
                    rwfullcoftank.save()
                    ReCalculate.ReCalculate(proposalID)
            return render(request, 'FacilityUI/risk_summary/fullyShellConsequence.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count,
                           'isTank': isBottom,
                           'isShell': isShell})
        else:
            material = models.RwMaterial.objects.get(id=proposalID)
            rwholezize = models.RwFullCoFHoleSize.objects.get(id=proposalID)
            ca = models.RwCaLevel1.objects.get(id=proposalID)
            inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
            data['model_fluid'] = inputCa.api_fluid
            data['toxic_fluid'] = inputCa.toxic_fluid
            data['material_cost'] = material.costfactor
            data['phase_fluid_storage'] = rwstream.storagephase
            data['toxic_fluid_percentage'] = inputCa.toxic_percent
            data['api_com_type'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=component.apicomponenttypeid).apicomponenttypename
            data['process_unit'] = roundData.roundMoney(inputCa.process_unit)
            data['equip_outage_multiplier'] = roundData.roundMoney((inputCa.outage_multiplier))
            data['production_cost'] = roundData.roundMoney(inputCa.production_cost)
            data['equipment_cost'] = roundData.roundMoney(inputCa.injure_cost)
            data['personal_density'] = inputCa.personal_density
            data['evironment_cost'] = roundData.roundMoney(inputCa.evironment_cost)
            data['ca_cmd'] = roundData.roundFC(ca.ca_cmd)
            data['ca_inj_flame'] = roundData.roundFC(ca.ca_inj_flame)
            data['gff_small'] = rwholezize.gff_small
            data['gff_medium'] = rwholezize.gff_medium
            data['gff_large'] = rwholezize.gff_large
            data['gff_rupture'] = rwholezize.gff_rupture
            data['MATERIAL_COST'] = material.costfactor
            data['max_operating_pressure'] = rwstream.maxoperatingpressure * 1000
            caflammable = CA_Flammable.CA_Flammable(data['model_fluid'], data['phase_fluid_storage'],
                                                    inputCa.mitigation_system, proposalID,
                                                    rwstream.maxoperatingtemperature + 273,
                                                    data['api_com_type'], data['toxic_fluid_percentage'],
                                                    data['toxic_fluid'])
            catoxic = ToxicConsequenceArea.CA_Toxic(proposalID, inputCa.toxic_fluid, caflammable.ReleasePhase(),
                                                    data['toxic_fluid_percentage'], data['api_com_type'],
                                                    data['model_fluid'], data['max_operating_pressure'])
            data['CA_cmd'] = caflammable.CA_Flam_Cmd()
            data['CA_inj'] = max(caflammable.CA_Flam_inj(), caflammable.CA_Flam_inj_toxic(), catoxic.CA_toxic_inj(),
                                 catoxic.CA_toxic_inj2(), catoxic.NoneCA_leck())
            fullcof = FinancialCOF.FinancialCOF(proposalID, data['model_fluid'], data['toxic_fluid'],
                                                data['toxic_fluid_percentage'], data['api_com_type'],
                                                data['MATERIAL_COST'], data['CA_cmd'], data['CA_inj'],
                                                data['phase_fluid_storage'], inputCa.mitigation_system,
                                                rwstream.maxoperatingtemperature + 273, data['max_operating_pressure'])
            data['Damage_outage_small'] = fullcof.outage_cmd_n(1)
            data['Damage_outage_medium'] = fullcof.outage_cmd_n(2)
            data['Damage_outage_large'] = fullcof.outage_cmd_n(3)
            data['Damage_outage_rupture'] = fullcof.outage_cmd_n(4)
            data['Equiment_cost_small'] = fullcof.HoleCost(1)
            data['Equiment_cost_medium'] = fullcof.HoleCost(2)
            data['Equiment_cost_large'] = fullcof.HoleCost(3)
            data['Equiment_cost_rupture'] = fullcof.HoleCost(4)
            data['frac_evap'] = roundData.roundFC(fullcof.frac_evap())
            data['FC_cmd'] = roundData.roundFC(fullcof.FC_cmd())
            data['FC_affa'] = roundData.roundFC(fullcof.FC_affa())
            data['outage_affa'] = roundData.roundFC(fullcof.Outage_affa())
            data['FC_prod'] = roundData.roundFC(fullcof.FC_prod())
            data['FC_inj'] = roundData.roundFC(fullcof.FC_inj())
            data['FC_env'] = roundData.roundFC(fullcof.FC_environ())
            data['outage_cmd'] = roundData.roundFC(fullcof.outage_cmd())
            data['fc_total'] = roundData.roundFC(fullcof.FC_total())
            data['fcof_category'] = fullcof.FC_Category()
            return render(request, 'FacilityUI/risk_summary/fullyNormalConsequence.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session, 'noti': noti, 'countnoti': countnoti, 'count': count,
                           'isTank': isBottom,
                           'isShell': isShell})
    except Exception as e:
        print(e)
        raise Http404


def AreaBasedCoF(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    data = {}
    try:
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 9 or component.componenttypeid_id == 13:
            isShell = 1
        else:
            isShell = 0
        # datdz sua
        if isShell:
            rwassessment = models.RwAssessment.objects.get(id=proposalID)
            rwequipment = models.RwEquipment.objects.get(id=proposalID)
            rwcomponent = models.RwComponent.objects.get(id=proposalID)
            rwstream = models.RwStream.objects.get(id=proposalID)
            rwexcor = models.RwExtcorTemperature.objects.get(id=proposalID)
            rwcoat = models.RwCoating.objects.get(id=proposalID)
            rwmaterial = models.RwMaterial.objects.get(id=proposalID)
            rwinputca = models.RwInputCaTank.objects.get(id=proposalID)
            countRwcatank = models.RwCaTank.objects.filter(id=proposalID)
            countRefullPOF = models.RwFullPof.objects.filter(id=proposalID)
            damageMachinsm = models.RwDamageMechanism.objects.filter(id_dm=proposalID)
            countRefullfc = models.RwFullFcof.objects.filter(id=proposalID)
            chart = models.RwDataChart.objects.filter(id=proposalID)
            FullFCof = models.RwFullFcof.objects.filter(id=proposalID)
            rwFullCofTank = models.RWFullCofTank.objects.get(id=proposalID)
            comp = models.ComponentMaster.objects.get(componentid=rwassessment.componentid_id)
            eq = models.EquipmentMaster.objects.get(equipmentid=rwassessment.equipmentid_id)
            target = models.FacilityRiskTarget.objects.get(facilityid=eq.facilityid_id)
            datafaci = models.Facility.objects.get(facilityid=eq.facilityid_id)
            comptype = models.ComponentType.objects.get(componenttypeid=comp.componenttypeid_id)

            cashell = CA_CAL.CA_SHELL(rwinputca.api_fluid, rwstream.fluidheight, rwinputca.shell_course_height,
                                      rwinputca.tank_diametter,
                                      rwinputca.environ_sensitivity,
                                      rwstream.fluidleavedikepercent, rwstream.fluidleavedikeremainonsitepercent,
                                      rwstream.fluidgooffsitepercent, rwmaterial.costfactor,
                                      models.ApiComponentType.objects.get(
                                          apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename,
                                      rwinputca.productioncost, rwinputca.soil_type,
                                      rwinputca.tank_fluid, rwcomponent.shellheight, rwinputca.productioncost,
                                      rwFullCofTank.equipoutagemultiplier,
                                      rwFullCofTank.equipcost, rwFullCofTank.popdens, rwFullCofTank.injcost,
                                      rwstream.releasefluidpercenttoxic, rwstream.storagephase, proposalID)
            data['hydraulic_water'] = roundData.roundFC(cashell.k_h_water())
            data['hydraulic_fluid'] = roundData.roundFC(cashell.k_h_prod())
            data['product_velocity'] = roundData.roundFC(cashell.vel_s_prod())
            data['flow_rate_d1'] = roundData.roundFC(cashell.W_n_Tank(1))
            data['flow_rate_d2'] = roundData.roundFC(cashell.W_n_Tank(2))
            data['flow_rate_d3'] = roundData.roundFC(cashell.W_n_Tank(3))
            data['flow_rate_d4'] = roundData.roundFC(cashell.W_n_Tank(4))
            data['liquid_height_shell'] = roundData.roundFC(cashell.LHT_above())
            data['fluid_above'] = roundData.roundFC(cashell.Lvol_abouve())
            data['area_small'] = roundData.roundFC(cashell.a_n_shell(1))
            data['area_medium'] = roundData.roundFC(cashell.a_n_shell(2))
            data['area_large'] = roundData.roundFC(cashell.a_n_shell(3))
            data['area_rupture'] = roundData.roundFC(cashell.a_n_shell(4))
            data['leak_duration_d1'] = roundData.roundFC(cashell.ld_tank(1))
            data['leak_duration_d2'] = roundData.roundFC(cashell.ld_tank(2))
            data['leak_duration_d3'] = roundData.roundFC(cashell.ld_tank(3))
            data['leak_duration_d4'] = roundData.roundFC(cashell.ld_tank(4))
            data['release_volume_leak_d1'] = roundData.roundFC(cashell.Bbl_leak_n(1))
            data['release_volume_leak_d2'] = roundData.roundFC(cashell.Bbl_leak_n(2))
            data['release_volume_leak_d3'] = roundData.roundFC(cashell.Bbl_leak_n(3))
            data['release_volume_leak_d4'] = roundData.roundFC(cashell.Bbl_leak_n(4))
            data['release_volume_rupture'] = roundData.roundFC(cashell.Bbl_leak_release())
            data['release_rate_1'] = roundData.roundFC(cashell.rate_Flammable(1))
            data['release_rate_2'] = roundData.roundFC(cashell.rate_Flammable(2))
            data['release_rate_3'] = roundData.roundFC(cashell.rate_Flammable(3))
            data['release_rate_4'] = roundData.roundFC(cashell.rate_Flammable(4))
            data['cainl_cmd_a'] = cashell.a_cmd(1)
            data['cainl_cmd_b'] = cashell.b_cmd(1)
            data['cail_cmd_a'] = cashell.a_cmd(2)
            data['cail_cmd_b'] = cashell.b_cmd(2)

            data['cainl_inj_a'] = cashell.a_inj(1)
            data['cainl_inj_b'] = cashell.b_inj(1)
            data['cail_inj_a'] = cashell.a_inj(2)
            data['cail_inj_b'] = cashell.b_inj(2)

            data['ca_cmd_ainl_cont_1'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 1))
            data['ca_cmd_ainl_cont_2'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 2))
            data['ca_cmd_ainl_cont_3'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 3))
            data['ca_cmd_ainl_cont_4'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 4))

            data['ca_cmd_ail_cont_1'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 1))
            data['ca_cmd_ail_cont_2'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 2))
            data['ca_cmd_ail_cont_3'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 3))
            data['ca_cmd_ail_cont_4'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 4))

            data['ca_inj_ainl_cont_1'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 1))
            data['ca_inj_ainl_cont_2'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 2))
            data['ca_inj_ainl_cont_3'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 3))
            data['ca_inj_ainl_cont_4'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 4))

            data['ca_inj_ail_cont_1'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 1))
            data['ca_inj_ail_cont_2'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 2))
            data['ca_inj_ail_cont_3'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 3))
            data['ca_inj_ail_cont_4'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 4))

            data['blend_ca_cmd_ainl_cont_1'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 1))
            data['blend_ca_cmd_ainl_cont_2'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 2))
            data['blend_ca_cmd_ainl_cont_3'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 3))
            data['blend_ca_cmd_ainl_cont_4'] = roundData.roundFC(cashell.ca_cmdn_ainl_cont(1, 4))

            data['blend_ca_cmd_ail_cont_1'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 1))
            data['blend_ca_cmd_ail_cont_2'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 2))
            data['blend_ca_cmd_ail_cont_3'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 3))
            data['blend_ca_cmd_ail_cont_4'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 4))

            data['blend_ca_inj_ainl_cont_1'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 1))
            data['blend_ca_inj_ainl_cont_2'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 2))
            data['blend_ca_inj_ainl_cont_3'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 3))
            data['blend_ca_inj_ainl_cont_4'] = roundData.roundFC(cashell.ca_inj_ainl_cont(1, 4))

            data['blend_ca_inj_ail_cont_1'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 1))
            data['blend_ca_inj_ail_cont_2'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 2))
            data['blend_ca_inj_ail_cont_3'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 3))
            data['blend_ca_inj_ail_cont_4'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 4))

            data['AIT_cmd_ca_1'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 1))
            data['AIT_cmd_ca_2'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 2))
            data['AIT_cmd_ca_3'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 3))
            data['AIT_cmd_ca_4'] = roundData.roundFC(cashell.ca_cmdn_ail_cont(2, 4))

            data['AIT_inj_ca_1'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 1))
            data['AIT_inj_ca_2'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 2))
            data['AIT_inj_ca_3'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 3))
            data['AIT_inj_ca_4'] = roundData.roundFC(cashell.ca_inj_ail_cont(2, 4))

            data['CA_Flam_Cmd_shell'] = roundData.roundFC(cashell.CA_Flam_Cmd_shell())
            data['CA_Flam_inj_shell'] = roundData.roundFC(cashell.CA_Flam_inj_shell())

            data['ld_toxic_shell_1'] = roundData.roundFC(cashell.leakDurationToxic(1))
            data['ld_toxic_shell_2'] = roundData.roundFC(cashell.leakDurationToxic(2))
            data['ld_toxic_shell_3'] = roundData.roundFC(cashell.leakDurationToxic(3))
            data['ld_toxic_shell_4'] = roundData.roundFC(cashell.leakDurationToxic(4))
            data['mass_rate_shell_1'] = roundData.roundFC(cashell.releaseRateMass(1))
            data['mass_rate_shell_2'] = roundData.roundFC(cashell.releaseRateMass(2))
            data['mass_rate_shell_3'] = roundData.roundFC(cashell.releaseRateMass(3))
            data['mass_rate_shell_4'] = roundData.roundFC(cashell.releaseRateMass(4))

            data['Constant_C_1'] = roundData.roundFC(cashell.ConstC(1))
            data['Constant_C_2'] = roundData.roundFC(cashell.ConstC(2))
            data['Constant_C_3'] = roundData.roundFC(cashell.ConstC(3))
            data['Constant_C_4'] = roundData.roundFC(cashell.ConstC(4))
            data['Constant_D_1'] = roundData.roundFC(cashell.ConstD(1))
            data['Constant_D_2'] = roundData.roundFC(cashell.ConstD(2))
            data['Constant_D_3'] = roundData.roundFC(cashell.ConstD(3))
            data['Constant_D_4'] = roundData.roundFC(cashell.ConstD(4))

            data['CA_toxic_shell1'] = roundData.roundFC(cashell.toxic_Inj(1))
            data['CA_toxic_shell2'] = roundData.roundFC(cashell.toxic_Inj(2))
            data['CA_toxic_shell3'] = roundData.roundFC(cashell.toxic_Inj(3))
            data['CA_toxic_shell4'] = roundData.roundFC(cashell.toxic_Inj(4))
            data['CA_toxic_fi'] = roundData.roundFC(cashell.total_toxic_Inj())

            data['CA_final_Com'] = roundData.roundFC(cashell.CA_Flam_Cmd_shell())
            data['CA_final_Per'] = roundData.roundFC(cashell.max_total_inj())
            data['CA_final'] = roundData.roundFC(cashell.FC_total_shell())
            return render(request, 'FacilityUI/risk_summary/areaBasedCoFforShell.html',
                          {'page': 'AreaBasedCoFShell', 'noti': noti, 'countnoti': countnoti, 'count': count,
                           'proposalID': proposalID, 'ass': rwAss, 'data': data, 'info': request.session,
                           'isTank': isBottom,
                           'isShell': isShell})
        elif isBottom:
            bottomConsequences = models.RwCaTank.objects.get(id=proposalID)
        else:
            ca = models.RwCaLevel1.objects.get(id=proposalID)
            apiComType = models.ApiComponentType.objects.get(apicomponenttypeid=component.apicomponenttypeid)
            inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
            rwcomponent = models.RwComponent.objects.get(id=proposalID)
            rwstream = models.RwStream.objects.get(id=proposalID)
            rwcalevel1 = models.RwCaLevel1.objects.get(id=proposalID)
            rwcofholesize = models.RwFullCoFHoleSize.objects.get(id=proposalID)
            data['ca_final'] = ca.ca_final
            data['fcof_category'] = ca.fcof_category
            data['api_comp_type'] = apiComType.apicomponenttypename
            data['diameter'] = rwcomponent.nominaldiameter
            data['liquidlevel'] = rwstream.liquidlevel
            data['componentvolume'] = rwcomponent.componentvolume
            data['model_fluid'] = inputCa.api_fluid
            data['toxic_fluid'] = inputCa.toxic_fluid
            data['toxic_fluid_percentage'] = inputCa.toxic_percent
            data['phase_fluid_storage'] = rwstream.storagephase
            data['max_operating_temp'] = rwstream.maxoperatingtemperature
            data['max_operating_pressure'] = rwstream.maxoperatingpressure * 1000
            data['ambient_state'] = rwcalevel1.ambient
            data['ideal_gas'] = rwcalevel1.ideal_gas
            data['ideal_gas_ratio'] = rwcalevel1.ideal_gas_ratio
            data['release_magnitude'] = rwcalevel1.fact_di
            data['liquid_density'] = rwcalevel1.liquid_density
            data['CA_reduction'] = rwcalevel1.fact_mit
            data['auto_ignition'] = rwcalevel1.auto_ignition
            data['release_phase'] = rwcalevel1.release_phase
            data['mw'] = rwcalevel1.mw
            data['nbp'] = rwcalevel1.nbp
            data['api_com_type'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=component.apicomponenttypeid).apicomponenttypename
            data['model_fluid_type'] = rwcalevel1.model_fluid_type
            data['toxic_fluid_type'] = rwcalevel1.toxic_fluid_type
            data['an_small'] = roundData.roundFC(rwcofholesize.an_small)
            data['an_medium'] = roundData.roundFC(rwcofholesize.an_medium)
            data['an_large'] = roundData.roundFC(rwcofholesize.an_large)
            data['an_rupture'] = roundData.roundFC(rwcofholesize.an_rupture)
            data['wn_small'] = roundData.roundFC(rwcofholesize.wn_small)
            data['wn_medium'] = roundData.roundFC(rwcofholesize.wn_medium)
            data['wn_large'] = roundData.roundFC(rwcofholesize.wn_large)
            data['wn_rupture'] = roundData.roundFC(rwcofholesize.wn_rupture)
            data['gff_n_small'] = rwcofholesize.gff_small
            data['gff_n_medium'] = rwcofholesize.gff_medium
            data['gff_n_large'] = rwcofholesize.gff_large
            data['gff_n_rupture'] = rwcofholesize.gff_rupture
            data['mass_add_n_small'] = roundData.roundFC(rwcofholesize.mass_add_n_small)
            data['mass_add_n_medium'] = roundData.roundFC(rwcofholesize.mass_add_n_medium)
            data['mass_add_n_large'] = roundData.roundFC(rwcofholesize.mass_add_n_large)
            data['mass_add_n_rupture'] = roundData.roundFC(rwcofholesize.mass_add_n_rupture)
            data['mass_avail_n_small'] = roundData.roundFC(rwcofholesize.mass_avail_n_small)
            data['mass_avail_n_medium'] = roundData.roundFC(rwcofholesize.mass_avail_n_medium)
            data['mass_avail_n_large'] = roundData.roundFC(rwcofholesize.mass_avail_n_large)
            data['mass_avail_n_rupture'] = roundData.roundFC(rwcofholesize.mass_avail_n_rupture)
            data['t_n_small'] = roundData.roundFC(rwcofholesize.t_n_small)
            data['t_n_medium'] = roundData.roundFC(rwcofholesize.t_n_medium)
            data['t_n_large'] = roundData.roundFC(rwcofholesize.t_n_large)
            data['t_n_rupture'] = roundData.roundFC(rwcofholesize.t_n_rupture)
            data['releasetype_small'] = rwcofholesize.releasetype_small[0:8]
            data['releasetype_medium'] = rwcofholesize.releasetype_medium[0:8]
            data['releasetype_large'] = rwcofholesize.releasetype_large[0:8]
            data['releasetype_rupture'] = rwcofholesize.releasetype_rupture[0:8]
            data['ld_max_n_small'] = rwcofholesize.ld_max_n_small
            data['ld_max_n_medium'] = rwcofholesize.ld_max_n_medium
            data['ld_max_n_large'] = rwcofholesize.ld_max_n_large
            data['ld_max_n_rupture'] = rwcofholesize.ld_max_n_rupture
            data['rate_n_small'] = roundData.roundFC(rwcofholesize.rate_n_small)
            data['rate_n_medium'] = roundData.roundFC(rwcofholesize.rate_n_medium)
            data['rate_n_large'] = roundData.roundFC(rwcofholesize.rate_n_large)
            data['rate_n_rupture'] = roundData.roundFC(rwcofholesize.rate_n_rupture)
            data['ld_n_small'] = roundData.roundFC(rwcofholesize.ld_n_small)
            data['ld_n_medium'] = roundData.roundFC(rwcofholesize.ld_n_medium)
            data['ld_n_large'] = roundData.roundFC(rwcofholesize.ld_n_large)
            data['ld_n_rupture'] = roundData.roundFC(rwcofholesize.ld_n_rupture)
            data['mass_n_small'] = roundData.roundFC(rwcofholesize.mass_n_small)
            data['mass_n_medium'] = roundData.roundFC(rwcofholesize.mass_n_medium)
            data['mass_n_large'] = roundData.roundFC(rwcofholesize.mass_n_large)
            data['mass_n_rupture'] = roundData.roundFC(rwcofholesize.mass_n_rupture)

            caflammable = CA_Flammable.CA_Flammable(data['model_fluid'], data['phase_fluid_storage'],
                                                    inputCa.mitigation_system, proposalID,
                                                    rwstream.minoperatingtemperature + 273,
                                                    data['api_com_type'], data['toxic_fluid_percentage'],
                                                    data['toxic_fluid'])
            catoxic = ToxicConsequenceArea.CA_Toxic(proposalID, inputCa.toxic_fluid, caflammable.ReleasePhase(),
                                                    data['toxic_fluid_percentage'], data['api_com_type'],
                                                    data['model_fluid'], data['max_operating_pressure'])

            # Consequence Analysis Properties
            data['Phase_of_Fluid'] = caflammable.ambient()
            data['release_phase_n'] = caflammable.ReleasePhase()
            # flammable CA_model
            data['cainl_cmd_a'] = caflammable.a_cmd(1)
            data['cainl_cmd_b'] = caflammable.b_cmd(1)
            data['cail_cmd_a'] = caflammable.a_cmd(2)
            data['cail_cmd_b'] = caflammable.b_cmd(2)
            data['iainl_cmd_a'] = caflammable.a_cmd(3)
            data['iainl_cmd_b'] = caflammable.b_cmd(3)
            data['iail_cmd_a'] = caflammable.a_cmd(4)
            data['iail_cmd_b'] = caflammable.b_cmd(4)

            data['cainl_inj_a'] = caflammable.a_inj(1)
            data['cainl_inj_b'] = caflammable.b_inj(1)
            data['cail_inj_a'] = caflammable.a_inj(2)
            data['cail_inj_b'] = caflammable.b_inj(2)
            data['iainl_inj_a'] = caflammable.a_inj(3)
            data['iainl_inj_b'] = caflammable.b_inj(3)
            data['iail_inj_a'] = caflammable.a_inj(4)
            data['iail_inj_b'] = caflammable.b_inj(4)

            data['cainl_cmd_cont_small'] = roundData.roundFC(caflammable.ca_cmdn_cont(1, 1))
            data['cainl_cmd_cont_medium'] = roundData.roundFC(caflammable.ca_cmdn_cont(1, 2))
            data['cainl_cmd_cont_large'] = roundData.roundFC(caflammable.ca_cmdn_cont(1, 3))
            data['cainl_cmd_cont_rupture'] = roundData.roundFC(caflammable.ca_cmdn_cont(1, 4))
            data['cail_cmd_cont_small'] = roundData.roundFC(caflammable.ca_cmdn_cont(2, 1))
            data['cail_cmd_cont_medium'] = roundData.roundFC(caflammable.ca_cmdn_cont(2, 2))
            data['cail_cmd_cont_large'] = roundData.roundFC(caflammable.ca_cmdn_cont(2, 3))
            data['cail_cmd_cont_rupture'] = roundData.roundFC(caflammable.ca_cmdn_cont(2, 4))
            data['iainl_cmd_cont_small'] = roundData.roundFC(caflammable.ca_cmdn_inst(3, 1))
            data['iainl_cmd_cont_medium'] = roundData.roundFC(caflammable.ca_cmdn_inst(3, 2))
            data['iainl_cmd_cont_large'] = roundData.roundFC(caflammable.ca_cmdn_inst(3, 3))
            data['iainl_cmd_cont_rupture'] = roundData.roundFC(caflammable.ca_cmdn_inst(3, 4))
            data['iail_cmd_cont_small'] = roundData.roundFC(caflammable.ca_cmdn_inst(4, 1))
            data['iail_cmd_cont_medium'] = roundData.roundFC(caflammable.ca_cmdn_inst(4, 2))
            data['iail_cmd_cont_large'] = roundData.roundFC(caflammable.ca_cmdn_inst(4, 3))
            data['iail_cmd_cont_rupture'] = roundData.roundFC(caflammable.ca_cmdn_inst(4, 4))

            data['cainl_inj_cont_small'] = roundData.roundFC(caflammable.ca_injn_cont(1, 1))
            data['cainl_inj_cont_medium'] = roundData.roundFC(caflammable.ca_injn_cont(1, 2))
            data['cainl_inj_cont_large'] = roundData.roundFC(caflammable.ca_injn_cont(1, 3))
            data['cainl_inj_cont_rupture'] = roundData.roundFC(caflammable.ca_injn_cont(1, 4))
            data['cail_inj_cont_small'] = roundData.roundFC(caflammable.ca_injn_cont(2, 1))
            data['cail_inj_cont_medium'] = roundData.roundFC(caflammable.ca_injn_cont(2, 2))
            data['cail_inj_cont_large'] = roundData.roundFC(caflammable.ca_injn_cont(2, 3))
            data['cail_inj_cont_rupture'] = roundData.roundFC(caflammable.ca_injn_cont(2, 4))
            data['iainl_inj_cont_small'] = roundData.roundFC(caflammable.ca_injn_inst(3, 1))
            data['iainl_inj_cont_medium'] = roundData.roundFC(caflammable.ca_injn_inst(3, 2))
            data['iainl_inj_cont_large'] = roundData.roundFC(caflammable.ca_injn_inst(3, 3))
            data['iainl_inj_cont_rupture'] = roundData.roundFC(caflammable.ca_injn_inst(3, 4))
            data['iail_inj_cont_small'] = roundData.roundFC(caflammable.ca_injn_inst(4, 1))
            data['iail_inj_cont_medium'] = roundData.roundFC(caflammable.ca_injn_inst(4, 2))
            data['iail_inj_cont_large'] = roundData.roundFC(caflammable.ca_injn_inst(4, 3))
            data['iail_inj_cont_rupture'] = roundData.roundFC(caflammable.ca_injn_inst(4, 4))

            data['blemding_cmd_ainl_small'] = roundData.roundFC(caflammable.CA_AINL_CMD_n(1))
            data['blemding_cmd_ainl_medium'] = roundData.roundFC(caflammable.CA_AINL_CMD_n(2))
            data['blemding_cmd_ainl_large'] = roundData.roundFC(caflammable.CA_AINL_CMD_n(3))
            data['blemding_cmd_ainl_rupture'] = roundData.roundFC(caflammable.CA_AINL_CMD_n(4))

            data['blemding_cmd_ail_small'] = roundData.roundFC(caflammable.CA_AIL_CMD_n(1))
            data['blemding_cmd_ail_medium'] = roundData.roundFC(caflammable.CA_AIL_CMD_n(2))
            data['blemding_cmd_ail_large'] = roundData.roundFC(caflammable.CA_AIL_CMD_n(3))
            data['blemding_cmd_ail_rupture'] = roundData.roundFC(caflammable.CA_AIL_CMD_n(4))

            data['blemding_inj_ainl_small'] = roundData.roundFC(caflammable.CA_AINL_INJ_n(1))
            data['blemding_inj_ainl_medium'] = roundData.roundFC(caflammable.CA_AINL_INJ_n(2))
            data['blemding_inj_ainl_large'] = roundData.roundFC(caflammable.CA_AINL_INJ_n(3))
            data['blemding_inj_ainl_rupture'] = roundData.roundFC(caflammable.CA_AINL_INJ_n(4))

            data['blemding_inj_ail_small'] = roundData.roundFC(caflammable.CA_AIL_INJ_n(1))
            data['blemding_inj_ail_medium'] = roundData.roundFC(caflammable.CA_AIL_INJ_n(2))
            data['blemding_inj_ail_large'] = roundData.roundFC(caflammable.CA_AIL_INJ_n(3))
            data['blemding_inj_ail_rupture'] = roundData.roundFC(caflammable.CA_AIL_INJ_n(4))

            data['ALT_cmd_small'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n(1))
            data['ALT_cmd_medium'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n(2))
            data['ALT_cmd_large'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n(3))
            data['ALT_cmd_rupture'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n(4))

            data['ALT_inj_small'] = roundData.roundFC(caflammable.CA_Flam_inj_n(1))
            data['ALT_inj_medium'] = roundData.roundFC(caflammable.CA_Flam_inj_n(2))
            data['ALT_inj_large'] = roundData.roundFC(caflammable.CA_Flam_inj_n(3))
            data['ALT_inj_rupture'] = roundData.roundFC(caflammable.CA_Flam_inj_n(4))

            data['eneff_n_small'] = rwcofholesize.eneff_n_small
            data['eneff_n_medium'] = rwcofholesize.eneff_n_medium
            data['eneff_n_large'] = rwcofholesize.eneff_n_large
            data['eneff_n_rupture'] = rwcofholesize.eneff_n_rupture
            data['factIC_n_small'] = roundData.roundFC(rwcofholesize.factIC_n_small)
            data['factIC_n_medium'] = roundData.roundFC(rwcofholesize.factIC_n_medium)
            data['factIC_n_large'] = roundData.roundFC(rwcofholesize.factIC_n_large)
            data['factIC_n_rupture'] = roundData.roundFC(rwcofholesize.factIC_n_rupture)

            data['ca_flam_cmd'] = roundData.roundFC(caflammable.CA_Flam_Cmd())
            data['ca_flam_inj'] = roundData.roundFC(caflammable.CA_Flam_inj())
            # Flammable CA_toxic
            data['cainl_cmd_a_toxic'] = caflammable.a_cmd_toxic(1)
            data['cainl_cmd_b_toxic'] = caflammable.b_cmd_toxic(1)
            data['cail_cmd_a_toxic'] = caflammable.a_cmd_toxic(2)
            data['cail_cmd_b_toxic'] = caflammable.b_cmd_toxic(2)
            data['iainl_cmd_a_toxic'] = caflammable.a_cmd_toxic(3)
            data['iainl_cmd_b_toxic'] = caflammable.b_cmd_toxic(3)
            data['iail_cmd_a_toxic'] = caflammable.a_cmd_toxic(4)
            data['iail_cmd_b_toxic'] = caflammable.b_cmd_toxic(4)

            data['cainl_inj_a_toxic'] = caflammable.a_inj_toxic(1)
            data['cainl_inj_b_toxic'] = caflammable.b_inj_toxic(1)
            data['cail_inj_a_toxic'] = caflammable.a_inj_toxic(2)
            data['cail_inj_b_toxic'] = caflammable.b_inj_toxic(2)
            data['iainl_inj_a_toxic'] = caflammable.a_inj_toxic(3)
            data['iainl_inj_b_toxic'] = caflammable.b_inj_toxic(3)
            data['iail_inj_a_toxic'] = caflammable.a_inj_toxic(4)
            data['iail_inj_b_toxic'] = caflammable.b_inj_toxic(4)

            data['cainl_cmd_cont_small_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(1, 1))
            data['cainl_cmd_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(1, 2))
            data['cainl_cmd_cont_large_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(1, 3))
            data['cainl_cmd_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(1, 4))
            data['cail_cmd_cont_small_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(2, 1))
            data['cail_cmd_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(2, 2))
            data['cail_cmd_cont_large_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(2, 3))
            data['cail_cmd_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_cmdn_cont_toxic(2, 4))
            data['iainl_cmd_cont_small_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(3, 1))
            data['iainl_cmd_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(3, 2))
            data['iainl_cmd_cont_large_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(3, 3))
            data['iainl_cmd_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(3, 4))
            data['iail_cmd_cont_small_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(4, 1))
            data['iail_cmd_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(4, 2))
            data['iail_cmd_cont_large_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(4, 3))
            data['iail_cmd_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_cmdn_inst_toxic(4, 4))

            data['cainl_inj_cont_small_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(1, 1))
            data['cainl_inj_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(1, 2))
            data['cainl_inj_cont_large_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(1, 3))
            data['cainl_inj_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(1, 4))
            data['cail_inj_cont_small_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(2, 1))
            data['cail_inj_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(2, 2))
            data['cail_inj_cont_large_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(2, 3))
            data['cail_inj_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_injn_cont_toxic(2, 4))
            data['iainl_inj_cont_small_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(3, 1))
            data['iainl_inj_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(3, 2))
            data['iainl_inj_cont_large_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(3, 3))
            data['iainl_inj_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(3, 4))
            data['iail_inj_cont_small_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(4, 1))
            data['iail_inj_cont_medium_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(4, 2))
            data['iail_inj_cont_large_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(4, 3))
            data['iail_inj_cont_rupture_toxic'] = roundData.roundFC(caflammable.ca_injn_inst_toxic(4, 4))

            data['blemding_cmd_ainl_small_toxic'] = roundData.roundFC(caflammable.CA_AINL_CMD_n_toxic(1))
            data['blemding_cmd_ainl_medium_toxic'] = roundData.roundFC(caflammable.CA_AINL_CMD_n_toxic(2))
            data['blemding_cmd_ainl_large_toxic'] = roundData.roundFC(caflammable.CA_AINL_CMD_n_toxic(3))
            data['blemding_cmd_ainl_rupture_toxic'] = roundData.roundFC(caflammable.CA_AINL_CMD_n_toxic(4))

            data['blemding_cmd_ail_small_toxic'] = roundData.roundFC(caflammable.CA_AIL_CMD_n_toxic(1))
            data['blemding_cmd_ail_medium_toxic'] = roundData.roundFC(caflammable.CA_AIL_CMD_n_toxic(2))
            data['blemding_cmd_ail_large_toxic'] = roundData.roundFC(caflammable.CA_AIL_CMD_n_toxic(3))
            data['blemding_cmd_ail_rupture_toxic'] = roundData.roundFC(caflammable.CA_AIL_CMD_n_toxic(4))

            data['blemding_inj_ainl_small_toxic'] = roundData.roundFC(caflammable.CA_AINL_INJ_n_toxic(1))
            data['blemding_inj_ainl_medium_toxic'] = roundData.roundFC(caflammable.CA_AINL_INJ_n_toxic(2))
            data['blemding_inj_ainl_large_toxic'] = roundData.roundFC(caflammable.CA_AINL_INJ_n_toxic(3))
            data['blemding_inj_ainl_rupture_toxic'] = roundData.roundFC(caflammable.CA_AINL_INJ_n_toxic(4))

            data['blemding_inj_ail_small_toxic'] = roundData.roundFC(caflammable.CA_AIL_INJ_n_toxic(1))
            data['blemding_inj_ail_medium_toxic'] = roundData.roundFC(caflammable.CA_AIL_INJ_n_toxic(2))
            data['blemding_inj_ail_large_toxic'] = roundData.roundFC(caflammable.CA_AIL_INJ_n_toxic(3))
            data['blemding_inj_ail_rupture_toxic'] = roundData.roundFC(caflammable.CA_AIL_INJ_n_toxic(4))

            data['ALT_cmd_small_toxic'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n_toxic(1))
            data['ALT_cmd_medium_toxic'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n_toxic(2))
            data['ALT_cmd_large_toxic'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n_toxic(3))
            data['ALT_cmd_rupture_toxic'] = roundData.roundFC(caflammable.CA_Flam_Cmd_n_toxic(4))

            data['ALT_inj_small_toxic'] = roundData.roundFC(caflammable.CA_Flam_inj_n_toxic(1))
            data['ALT_inj_medium_toxic'] = roundData.roundFC(caflammable.CA_Flam_inj_n_toxic(2))
            data['ALT_inj_large_toxic'] = roundData.roundFC(caflammable.CA_Flam_inj_n_toxic(3))
            data['ALT_inj_rupture_toxic'] = roundData.roundFC(caflammable.CA_Flam_inj_n_toxic(4))

            data['eneff_n_small'] = rwcofholesize.eneff_n_small
            data['eneff_n_medium'] = rwcofholesize.eneff_n_medium
            data['eneff_n_large'] = rwcofholesize.eneff_n_large
            data['eneff_n_rupture'] = rwcofholesize.eneff_n_rupture
            data['factIC_n_small_toxic'] = roundData.roundFC(rwcofholesize.factIC_n_small)
            data['factIC_n_medium_toxic'] = roundData.roundFC(rwcofholesize.factIC_n_medium)
            data['factIC_n_large_toxic'] = roundData.roundFC(rwcofholesize.factIC_n_large)
            data['factIC_n_rupture_toxic'] = roundData.roundFC(rwcofholesize.factIC_n_rupture)

            data['ca_flam_cmd_toxic'] = roundData.roundFC(caflammable.CA_Flam_Cmd_toxic())
            data['ca_flam_inj_toxic'] = roundData.roundFC(caflammable.CA_Flam_inj_toxic())
            # toxic1
            data['ld_tox_small'] = roundData.roundFC(catoxic.ld_tox_n(1))
            data['ld_tox_medium'] = roundData.roundFC(catoxic.ld_tox_n(2))
            data['ld_tox_large'] = roundData.roundFC(catoxic.ld_tox_n(3))
            data['ld_tox_rupture'] = roundData.roundFC(catoxic.ld_tox_n(4))
            data['Cont_C_small'] = catoxic.ContantC(1)
            data['Cont_C_medium'] = catoxic.ContantC(2)
            data['Cont_C_large'] = catoxic.ContantC(3)
            data['Cont_C_rupture'] = catoxic.ContantC(4)
            data['Cont_D_small'] = catoxic.ContantD(1)
            data['Cont_D_medium'] = catoxic.ContantD(2)
            data['Cont_D_large'] = catoxic.ContantD(3)
            data['Cont_D_rupture'] = catoxic.ContantD(4)
            data['Cont_E_small'] = catoxic.ContantE(1)
            data['Cont_E_medium'] = catoxic.ContantE(2)
            data['Cont_E_large'] = catoxic.ContantE(3)
            data['Cont_E_rupture'] = catoxic.ContantE(4)
            data['Cont_F_small'] = catoxic.ContantF(1)
            data['Cont_F_medium'] = catoxic.ContantF(2)
            data['Cont_F_large'] = catoxic.ContantF(3)
            data['Cont_F_rupture'] = catoxic.ContantF(4)

            data['rate_tox_small'] = roundData.roundFC(catoxic.Rate_tox_n(1))
            data['rate_tox_medium'] = roundData.roundFC(catoxic.Rate_tox_n(2))
            data['rate_tox_large'] = roundData.roundFC(catoxic.Rate_tox_n(3))
            data['rate_tox_rupture'] = roundData.roundFC(catoxic.Rate_tox_n(4))

            data['mass_tox_small'] = roundData.roundFC(catoxic.Mass_tox_n(1))
            data['mass_tox_medium'] = roundData.roundFC(catoxic.Mass_tox_n(2))
            data['mass_tox_large'] = roundData.roundFC(catoxic.Mass_tox_n(3))
            data['mass_tox_rupture'] = roundData.roundFC(catoxic.Mass_tox_n(4))

            data['toxic_ca_small'] = roundData.roundFC(catoxic.CA_injn_tox(1))
            data['toxic_ca_medium'] = roundData.roundFC(catoxic.CA_injn_tox(2))
            data['toxic_ca_large'] = roundData.roundFC(catoxic.CA_injn_tox(3))
            data['toxic_ca_rupture'] = roundData.roundFC(catoxic.CA_injn_tox(4))

            data['CA_toxic_inj'] = roundData.roundFC(catoxic.CA_toxic_inj())
            # toxic2
            data['Cont_C_small2'] = catoxic.ContantC_toxic2(1)
            data['Cont_C_medium2'] = catoxic.ContantC_toxic2(2)
            data['Cont_C_large2'] = catoxic.ContantC_toxic2(3)
            data['Cont_C_rupture2'] = catoxic.ContantC_toxic2(4)
            data['Cont_D_small2'] = catoxic.ContantD_toxic2(1)
            data['Cont_D_medium2'] = catoxic.ContantD_toxic2(2)
            data['Cont_D_large2'] = catoxic.ContantD_toxic2(3)
            data['Cont_D_rupture2'] = catoxic.ContantD_toxic2(4)
            data['Cont_E_small2'] = catoxic.ContantE_toxic2(1)
            data['Cont_E_medium2'] = catoxic.ContantE_toxic2(2)
            data['Cont_E_large2'] = catoxic.ContantE_toxic2(3)
            data['Cont_E_rupture2'] = catoxic.ContantE_toxic2(4)
            data['Cont_F_small2'] = catoxic.ContantF_toxic2(1)
            data['Cont_F_medium2'] = catoxic.ContantF_toxic2(2)
            data['Cont_F_large2'] = catoxic.ContantF_toxic2(3)
            data['Cont_F_rupture2'] = catoxic.ContantF_toxic2(4)

            data['toxic_ca_small2'] = roundData.roundFC(catoxic.CA_injn_tox2(1))
            data['toxic_ca_medium2'] = roundData.roundFC(catoxic.CA_injn_tox2(2))
            data['toxic_ca_large2'] = roundData.roundFC(catoxic.CA_injn_tox2(3))
            data['toxic_ca_rupture2'] = roundData.roundFC(catoxic.CA_injn_tox2(4))

            data['CA_toxic_inj2'] = roundData.roundFC(catoxic.CA_toxic_inj2())
            # non
            data['NoneCA_cont_Inj_1'] = roundData.roundFC(catoxic.NoneCA_cont_Inj_n(1))
            data['NoneCA_cont_Inj_2'] = roundData.roundFC(catoxic.NoneCA_cont_Inj_n(2))
            data['NoneCA_cont_Inj_3'] = roundData.roundFC(catoxic.NoneCA_cont_Inj_n(3))
            data['NoneCA_cont_Inj_4'] = roundData.roundFC(catoxic.NoneCA_cont_Inj_n(4))
            data['NoneCA_Inst_Inj_1'] = roundData.roundFC(catoxic.NoneCA_Inst_Inj_n(1))
            data['NoneCA_Inst_Inj_2'] = roundData.roundFC(catoxic.NoneCA_Inst_Inj_n(2))
            data['NoneCA_Inst_Inj_3'] = roundData.roundFC(catoxic.NoneCA_Inst_Inj_n(3))
            data['NoneCA_Inst_Inj_4'] = roundData.roundFC(catoxic.NoneCA_Inst_Inj_n(4))
            data['NoneCA_leck_Inj_1'] = roundData.roundFC(catoxic.NoneCA_leck_Inj_n(1))
            data['NoneCA_leck_Inj_2'] = roundData.roundFC(catoxic.NoneCA_leck_Inj_n(2))
            data['NoneCA_leck_Inj_3'] = roundData.roundFC(catoxic.NoneCA_leck_Inj_n(3))
            data['NoneCA_leck_Inj_4'] = roundData.roundFC(catoxic.NoneCA_leck_Inj_n(4))
            data['NoneCA_leck'] = roundData.roundFC(catoxic.NoneCA_leck())
            data['CA_total'] = roundData.roundFC(catoxic.CA_total(data['ca_flam_cmd'], data['ca_flam_inj']))
            data['CA_Category'] = catoxic.CA_Category(data['ca_flam_cmd'], data['ca_flam_inj'])
            return render(request, 'FacilityUI/risk_summary/areaBasedCoFforNormal.html',
                          {'page': 'areaBasedCoF', 'noti': noti, 'countnoti': countnoti, 'count': count,
                           'proposalID': proposalID, 'ass': rwAss, 'data': data, 'info': request.session,
                           'isTank': isBottom,
                           'isShell': isShell})

    except Exception as e:
        print(e)
        raise Http404


def AreaBasedCoFShell(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    data = {}
    try:
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 9 or component.componenttypeid_id == 13:
            isShell = 1
        else:
            isShell = 0
        ca = models.RwCaLevel1.objects.get(id=proposalID)
        apiComType = models.ApiComponentType.objects.get(apicomponenttypeid=component.apicomponenttypeid)
        inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwstream = models.RwStream.objects.get(id=proposalID)
        rwcalevel1 = models.RwCaLevel1.objects.get(id=proposalID)
        rwcofholesize = models.RwFullCoFHoleSize.objects.get(id=proposalID)
    except Exception as e:
        print(e)
    return render(request, 'FacilityUI/risk_summary/areaBasedCoFforShell.html',
                  {'page': 'AreaBasedCoFShell', 'noti': noti, 'countnoti': countnoti, 'count': count,
                   'proposalID': proposalID, 'ass': rwAss, 'data': data, 'info': request.session, 'isTank': isBottom,
                   'isShell': isShell})


def RiskChart(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    list = []
    time = []
    listDamage = []
    OldProsal = 0
    thiningToTal = []
    ext = []
    scc = []
    htha = []
    brit = []
    pipe = []
    try:
        listDamage = ReCalculate.caculateRiskChart(proposalID)
        for a in listDamage[0]:
            thiningToTal.append(a)
        for a in listDamage[1]:
            ext.append(a)
        for a in listDamage[2]:
            scc.append(a)
        for a in listDamage[3]:
            htha.append(a)
        for a in listDamage[4]:
            brit.append(a)
        for a in listDamage[5]:
            pipe.append(a)

        rwAssesmentAll = models.RwAssessment.objects.all()
        rwAssessment = models.RwAssessment.objects.get(id=proposalID)
        comp = models.ComponentMaster.objects.get(componentid=rwAssessment.componentid_id)
        # print("1")
        assessmentDate = rwAssessment.assessmentdate
        timerNew = assessmentDate.year * 365 + assessmentDate.month * 30 + assessmentDate.day
        # print(timerNew)
        for a in rwAssesmentAll:
            if (a.componentid_id == comp.componentid):
                b = a.assessmentdate
                timerOld = b.year * 365 + b.month * 30 + b.day
                print(timerOld)
                H = timerNew - timerOld
                if (a.id != proposalID and H > 0):
                    list.append(a)
                    time.append(H)
        # print(list)
        # print(time)
        # datanew
        rwFullpof = models.RwFullPof.objects.get(id=proposalID)
        rwFullcof = models.RwFullFcof.objects.get(id=proposalID)
        risk = rwFullpof.pofap1 * rwFullcof.fcofvalue
        chart = models.RwDataChart.objects.get(id=proposalID)
        assessmentDate = rwAssessment.assessmentdate
        dataChart = [risk, chart.riskage1, chart.riskage2, chart.riskage3, chart.riskage4, chart.riskage5,
                     chart.riskage6,
                     chart.riskage7, chart.riskage8, chart.riskage9, chart.riskage9, chart.riskage10, chart.riskage11,
                     chart.riskage12, chart.riskage13, chart.riskage14, chart.riskage15]
        # print(dataChart)
        # xác dịnh Olddata
        if list:
            for a in list:
                b = a.assessmentdate
                timerOld = b.year * 365 + b.month * 30 + b.day
                H = timerNew - timerOld
                if (H == min(time)):
                    OldProsal = a.id
                    OldassessmentDate = a.assessmentdate
            # print(OldProsal)
            # print(proposalID)
            # dataOld
            rwFullpofOld = models.RwFullPof.objects.get(id=OldProsal)
            rwFullcofOld = models.RwFullFcof.objects.get(id=OldProsal)
            riskOld = rwFullpofOld.pofap1 * rwFullcofOld.fcofvalue
            chartOld = models.RwDataChart.objects.get(id=OldProsal)
            dataOldChart = [riskOld, chartOld.riskage1, chartOld.riskage2, chartOld.riskage3, chartOld.riskage4,
                            chartOld.riskage5, chartOld.riskage6,
                            chartOld.riskage7, chartOld.riskage8, chartOld.riskage9, chartOld.riskage9,
                            chartOld.riskage10, chartOld.riskage11,
                            chartOld.riskage12, chartOld.riskage13, chartOld.riskage14, chartOld.riskage15]
            dateold = OldassessmentDate.year * 365 + OldassessmentDate.month * 30 + OldassessmentDate.day
            i = (timerNew - dateold) / 365
            datachartCompine = dataOldChart[0:int(i)]
            for a in dataChart:
                datachartCompine.append(a)
            datachartFinal = datachartCompine[0:16]
            dataLabel = [date2Str.date2str(OldassessmentDate),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 1)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 2)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 3)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 4)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 5)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 6)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 7)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 8)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 9)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 10)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 11)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 12)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 13)),
                         date2Str.date2str(date2Str.dateFuture(OldassessmentDate, 14))]
        else:
            dataOldChart = dataChart
            datachartFinal = dataChart
            dataLabel = [date2Str.date2str(assessmentDate), date2Str.date2str(date2Str.dateFuture(assessmentDate, 1)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 2)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 3)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 4)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 5)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 6)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 7)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 8)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 9)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 10)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 11)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 12)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 13)),
                         date2Str.date2str(date2Str.dateFuture(assessmentDate, 14))]
        dataTarget = [chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget]
        endLabel = date2Str.date2str(date2Str.dateFuture(assessmentDate, 15))
        content = {'page': 'riskChart', 'label': dataLabel, 'data': dataOldChart, 'data1': datachartFinal,
                   'target': dataTarget, 'endLabel': endLabel, 'proposalname': rwAssessment.proposalname,
                   'proposalID': rwAssessment.id, 'componentID': rwAssessment.componentid_id, 'noti': noti,
                   'countnoti': countnoti, 'count': count, 'thiningToTal': thiningToTal, 'ext': ext, 'scc': scc,
                   'htha': htha, 'brit': brit, 'pipe': pipe}
        return render(request, 'FacilityUI/risk_summary/riskChart.html', content)
    except Exception as e:
        print("Exception")
        print(e)
        raise Http404


def ExportExcel(request, index, type):
    try:
        return export_data.excelExport(index, type)
    except:
        raise Http404


def upload(request, siteID, filename=""):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    dataSheet1=[]
    dataSheet2=[]
    dataSheet3=[]
    dataSheet4=[]
    dataSheet5=[]
    dataSheet6=[]
    dataSheet7=[]
    try:
        fs = FileSystemStorage()
        showcontent = "Choose plan process file"
        if filename:
            print("da lay duoc file name",filename)
            uploaded_file_url = fs.url(filename)
            url_file = settings.BASE_DIR.replace('\\', '//') + str(uploaded_file_url).replace('/', '//').replace(
                '%20', ' ')
            dataSheet1 = ExcelImport.getSheetEquip(url_file)
            dataSheet2 = ExcelImport.getSheetCom(url_file)
            dataSheet3 = ExcelImport.getSheetOperCon(url_file)
            dataSheet4 = ExcelImport.getSheetStream(url_file)
            dataSheet5 = ExcelImport.getSheetMaterial(url_file)
            dataSheet6 = ExcelImport.getSheetCoat(url_file)
            dataSheet7 = ExcelImport.getSheetFullCoF(url_file)

        try:
            if "import" in request.POST:
                myfile = request.FILES['myexcelFile']
                filename = fs.save(myfile.name, myfile)
                # print(filename)
                # uploaded_file_url = fs.url(filename)
                # url_file = settings.BASE_DIR.replace('\\', '//') + str(uploaded_file_url).replace('/', '//').replace(
                #     '%20', ' ')
                # link=url_file
                # print(link)
                return redirect('uploadPlan', siteID=siteID,filename=filename)
            if "submitFile" in request.POST:
                print("2")
                print(filename)
                uploaded_file_url = fs.url(filename)
                url_file = settings.BASE_DIR.replace('\\', '//') + str(uploaded_file_url).replace('/', '//').replace(
                    '%20', ' ')
                ExcelImport.importPlanProcess(url_file)
            # if request.method == 'POST' and request.FILES['myexcelFile']:
            #     print("myexcelFile")
            #     myfile = request.FILES['myexcelFile']
            #     fs = FileSystemStorage()
            #     filename = fs.save(myfile.name, myfile)
            #     print(filename)
            #     uploaded_file_url = fs.url(filename)
            #     print(uploaded_file_url)
            #     url_file = settings.BASE_DIR.replace('\\', '//') + str(uploaded_file_url).replace('/', '//').replace(
            #         '%20', ' ')
                # ExcelImport.importPlanProcess(url_file)
            #     print("go done")
            #     try:
            #         os.remove(url_file)
            #     except OSError:
            #         pass
        except Exception as e:
            print(e)
            print("ko co file")
        # try:
        #     if request.method == 'POST' and request.FILES['myexcelScada']:
        #         print("myexcelScada")
        # except:
        #     print("ko co file scada")
    except Exception as e:
        print(e)
        raise Http404

    return render(request, 'FacilityUI/facility/uploadData.html',
                  {'siteID': siteID, 'filename':filename ,'showcontent': showcontent,'dataSheet1':dataSheet1,'dataSheet2':dataSheet2,'dataSheet3':dataSheet3,'dataSheet4':dataSheet4,'dataSheet5':dataSheet5,'dataSheet6':dataSheet6,'dataSheet7':dataSheet7,'noti': noti, 'countnoti': countnoti, 'count': count,
                   'info': request.session, 'page': 'uploadPlan'})

def ImportExcel(request,url_file):
    return render(request, 'FacilityUI/facility/importExcel.html',
                  {'noti': noti, 'countnoti': countnoti, 'count': count,
                   'info': request.session, 'page': 'importexcel'})
def uploadInspPlan(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        showcontent = "Choose inspection history file"
        if request.method == 'POST' and request.FILES['myexcelFile']:
            myfile = request.FILES['myexcelFile']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            upload_url = fs.url(filename)
            url_file = settings.BASE_DIR.replace('\\', '//') + str(upload_url).replace('/', '//').replace('%20', ' ')
            ExcelImport.importInspectionPlan(url_file)
            try:
                os.remove(url_file)
            except OSError:
                pass
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/facility/uploadData.html',
                  {'siteID': siteID, 'showcontent': showcontent, 'noti': noti, 'countnoti': countnoti, 'count': count,
                   'info': request.session, 'page': 'uploadHistory'})


# def uploadSCADA(request, siteID):
#     noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
#     countnoti = noti.filter(state=0).count()
#     count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
#                                           Q(Is_see=0)).count()
#
#     return render(request, 'FacilityUI/facility/uploadSCADA.html',
#                   {'siteID': siteID, 'noti': noti, 'countnoti': countnoti, 'count': count,
#                    'info': request.session, 'page': 'uploadHistory'})
############### Dang Nhap Dang Suat #################
def ManagementSystems(request, facilityID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    faci = models.Facility.objects.get(facilityid=facilityID)
    data={}
    num=(10, 2, 2, 2, 2, 2, 10, 15, 10, 5, 5, 5, 5, 2, 2, 2, 10, 3, 3, 3, 5, 10, 8, 4, 4, 1, 1, 1, 1, 1, 1, 5, 8, 10, 5, 1, 1, 1, 1, 1, 2, 2, 2, 2,
                2,2,2,3,3,3,3,3,8,3,3,10,12,10,5,9,5,4,4,4,4,5,4,5,3,3,3,3,3,10,5,10,5,2,2,2,2,2,2,2,2,3,4,3,10,10,11,6,3,0,8,4,2,0,2,2,2,2,2,2,2,2,2,2,10,1,1,1,1,1,
                10,10,7,4,2,0,10,5,4,4,10,10,3,3,3,3,3,3,10,7,3,0,10,5,0,10,7,5,3,0,4,4,4,5,5,5,5,2,2,2,2,2,2,1,2,2,5,5,1,1,3,1,1,2,2,2,3,2,5,3,2,3,3,5,1,2,3,2,5,3,2,
                5,5,3,1,1,1,1,1,1,1,1,1,1,1,1,1,5,5,10,10,10,5,5,5,5,5,5,10,5,2,2,2,2,2,2,2,2,2,2,2,5,2,2,2,5,2,10,10,5,3,3,2,2,2,2,2,2,2,2,2,2,2,5,10,5,6,6,3,3,3,2,2,2,2,
                9,9,10,10,7,0,10,5,5,10,2,6,4,2,7,4,5,8,3,8,4)
    # if request.POST.get('check1'):
    #     print(num[0])
    # if request.POST.get('check2'):
    #     check[1]=2
    #     print('check[1]',check[1])
    if request.method == 'POST':
        for i in range(len(num)):
            score=0
            if request.POST.get('check1'):
                score+=num[0]
            if request.POST.get('check2'):
                score+=num[1]
            if request.POST.get('check3'):
                score+=num[2]
            if request.POST.get('check4'):
                score+=num[3]
            if request.POST.get('check5'):
                score+=num[4]
            if request.POST.get('check6'):
                score+=num[5]
            if request.POST.get('check7'):
                score+=num[6]
            if request.POST.get('check8'):
                score+=num[7]
            if request.POST.get('check9'):
                score+=num[8]
            if request.POST.get('check10'):
                score+=num[9]
            if request.POST.get('check11'):
                score+=num[10]
            if request.POST.get('check12'):
                score+=num[11]
            if request.POST.get('check13'):
                score+=num[12]
            if request.POST.get('check14'):
                score+=num[13]
            if request.POST.get('check15'):
                score+=num[14]
            if request.POST.get('check16'):
                score+=num[15]
            if request.POST.get('check17'):
                score+=num[16]
            if request.POST.get('check18'):
                score+=num[17]
            if request.POST.get('check19'):
                score+=num[18]
            if request.POST.get('check20'):
                score+=num[19]
            if request.POST.get('check21'):
                score+=num[20]
            if request.POST.get('check22'):
                score+=num[21]
            if request.POST.get('check23'):
                score+=num[22]
            if request.POST.get('check24'):
                score+=num[23]
            if request.POST.get('check25'):
                score+=num[24]
            if request.POST.get('check26'):
                score+=num[25]
            if request.POST.get('check27'):
                score+=num[26]
            if request.POST.get('check28'):
                score+=num[27]
            if request.POST.get('check29'):
                score+=num[28]
            if request.POST.get('check30'):
                score+=num[29]
            if request.POST.get('check31'):
                score+=num[30]
            if request.POST.get('check32'):
                score+=num[31]
            if request.POST.get('check33'):
                score+=num[32]
            if request.POST.get('check34'):
                score+=num[33]
            if request.POST.get('check35'):
                score+=num[34]
            if request.POST.get('check36'):
                score+=num[35]
            if request.POST.get('check37'):
                score+=num[36]
            if request.POST.get('check38'):
                score+=num[37]
            if request.POST.get('check39'):
                score+=num[38]
            if request.POST.get('check40'):
                score+=num[39]
            if request.POST.get('check41'):
                score+=num[40]
            if request.POST.get('check42'):
                score+=num[41]
            if request.POST.get('check43'):
                score+=num[42]
            if request.POST.get('check44'):
                score+=num[43]
            if request.POST.get('check45'):
                score+=num[44]
            if request.POST.get('check46'):
                score+=num[45]
            if request.POST.get('check47'):
                score+=num[46]
            if request.POST.get('check48'):
                score+=num[47]
            if request.POST.get('check49'):
                score+=num[48]
            if request.POST.get('check50'):
                score+=num[49]
            if request.POST.get('check51'):
                score+=num[50]
            if request.POST.get('check52'):
                score+=num[51]
            if request.POST.get('check53'):
                score+=num[52]
            if request.POST.get('check54'):
                score+=num[53]
            if request.POST.get('check55'):
                score+=num[54]
            if request.POST.get('check56'):
                score+=num[55]
            if request.POST.get('check57'):
                score+=num[56]
            if request.POST.get('check58'):
                score+=num[57]
            if request.POST.get('check59'):
                score+=num[58]
            if request.POST.get('check60'):
                score+=num[59]
            if request.POST.get('check61'):
                score+=num[60]
            if request.POST.get('check62'):
                score+=num[61]
            if request.POST.get('check63'):
                score+=num[62]
            if request.POST.get('check64'):
                score+=num[63]
            if request.POST.get('check65'):
                score+=num[64]
            if request.POST.get('check66'):
                score+=num[65]
            if request.POST.get('check67'):
                score+=num[66]
            if request.POST.get('check68'):
                score+=num[67]
            if request.POST.get('check69'):
                score+=num[68]
            if request.POST.get('check70'):
                score+=num[69]
            if request.POST.get('check71'):
                score+=num[70]
            if request.POST.get('check72'):
                score+=num[71]
            if request.POST.get('check73'):
                score+=num[72]
            if request.POST.get('check74'):
                score+=num[73]
            if request.POST.get('check75'):
                score+=num[74]
            if request.POST.get('check76'):
                score+=num[75]
            if request.POST.get('check77'):
                score+=num[76]
            if request.POST.get('check78'):
                score+=num[77]
            if request.POST.get('check79'):
                score+=num[78]
            if request.POST.get('check80'):
                score+=num[79]
            if request.POST.get('check81'):
                score+=num[80]
            if request.POST.get('check82'):
                score+=num[81]
            if request.POST.get('check83'):
                score+=num[82]
            if request.POST.get('check84'):
                score+=num[83]
            if request.POST.get('check85'):
                score+=num[84]
            if request.POST.get('check86'):
                score+=num[85]
            if request.POST.get('check87'):
                score+=num[86]
            if request.POST.get('check88'):
                score+=num[87]
            if request.POST.get('check89'):
                score+=num[88]
            if request.POST.get('check90'):
                score+=num[89]
            if request.POST.get('check91'):
                score+=num[90]
            if request.POST.get('check92'):
                score+=num[91]
            if request.POST.get('check93'):
                score+=num[92]
            if request.POST.get('check94'):
                score+=num[93]
            if request.POST.get('check95'):
                score+=num[94]
            if request.POST.get('check96'):
                score+=num[95]
            if request.POST.get('check97'):
                score+=num[96]
            if request.POST.get('check98'):
                score+=num[97]
            if request.POST.get('check99'):
                score+=num[98]
            if request.POST.get('check100'):
                score+=num[99]
            if request.POST.get('check101'):
                score+=num[100]
            if request.POST.get('check102'):
                score+=num[101]
            if request.POST.get('check103'):
                score+=num[102]
            if request.POST.get('check104'):
                score+=num[103]
            if request.POST.get('check105'):
                score+=num[104]
            if request.POST.get('check106'):
                score+=num[105]
            if request.POST.get('check107'):
                score+=num[106]
            if request.POST.get('check108'):
                score+=num[107]
            if request.POST.get('check109'):
                score+=num[108]
            if request.POST.get('check110'):
                score+=num[109]
            if request.POST.get('check111'):
                score+=num[110]
            if request.POST.get('check112'):
                score+=num[111]
            if request.POST.get('check113'):
                score+=num[112]
            if request.POST.get('check114'):
                score+=num[113]
            if request.POST.get('check115'):
                score+=num[114]
            if request.POST.get('check116'):
                score+=num[115]
            if request.POST.get('check117'):
                score+=num[116]
            if request.POST.get('check118'):
                score+=num[117]
            if request.POST.get('check119'):
                score+=num[118]
            if request.POST.get('check120'):
                score+=num[119]
            if request.POST.get('check121'):
                score+=num[120]
            if request.POST.get('check122'):
                score+=num[121]
            if request.POST.get('check123'):
                score+=num[122]
            if request.POST.get('check124'):
                score+=num[123]
            if request.POST.get('check125'):
                score+=num[124]
            if request.POST.get('check126'):
                score+=num[125]
            if request.POST.get('check127'):
                score+=num[126]
            if request.POST.get('check128'):
                score+=num[127]
            if request.POST.get('check129'):
                score+=num[128]
            if request.POST.get('check130'):
                score+=num[129]
            if request.POST.get('check131'):
                score+=num[130]
            if request.POST.get('check132'):
                score+=num[131]
            if request.POST.get('check133'):
                score+=num[132]
            if request.POST.get('check134'):
                score+=num[133]
            if request.POST.get('check135'):
                score+=num[134]
            if request.POST.get('check136'):
                score+=num[135]
            if request.POST.get('check137'):
                score+=num[136]
            if request.POST.get('check138'):
                score+=num[137]
            if request.POST.get('check139'):
                score+=num[138]
            if request.POST.get('check140'):
                score+=num[139]
            if request.POST.get('check141'):
                score+=num[140]
            if request.POST.get('check142'):
                score+=num[141]
            if request.POST.get('check143'):
                score+=num[142]
            if request.POST.get('check144'):
                score+=num[143]
            if request.POST.get('check145'):
                score+=num[144]
            if request.POST.get('check146'):
                score+=num[145]
            if request.POST.get('check147'):
                score+=num[146]
            if request.POST.get('check148'):
                score+=num[147]
            if request.POST.get('check149'):
                score+=num[148]
            if request.POST.get('check150'):
                score+=num[149]
            if request.POST.get('check151'):
                score+=num[150]
            if request.POST.get('check152'):
                score+=num[151]
            if request.POST.get('check153'):
                score+=num[152]
            if request.POST.get('check154'):
                score+=num[153]
            if request.POST.get('check155'):
                score+=num[154]
            if request.POST.get('check156'):
                score+=num[155]
            if request.POST.get('check157'):
                score+=num[156]
            if request.POST.get('check158'):
                score+=num[157]
            if request.POST.get('check159'):
                score+=num[158]
            if request.POST.get('check160'):
                score+=num[159]
            if request.POST.get('check161'):
                score+=num[160]
            if request.POST.get('check162'):
                score+=num[161]
            if request.POST.get('check163'):
                score+=num[162]
            if request.POST.get('check164'):
                score+=num[163]
            if request.POST.get('check165'):
                score+=num[164]
            if request.POST.get('check166'):
                score+=num[165]
            if request.POST.get('check167'):
                score+=num[166]
            if request.POST.get('check168'):
                score+=num[167]
            if request.POST.get('check169'):
                score+=num[168]
            if request.POST.get('check170'):
                score+=num[169]
            if request.POST.get('check171'):
                score+=num[170]
            if request.POST.get('check172'):
                score+=num[171]
            if request.POST.get('check173'):
                score+=num[172]
            if request.POST.get('check174'):
                score+=num[173]
            if request.POST.get('check175'):
                score+=num[174]
            if request.POST.get('check176'):
                score+=num[175]
            if request.POST.get('check177'):
                score+=num[176]
            if request.POST.get('check178'):
                score+=num[177]
            if request.POST.get('check179'):
                score+=num[178]
            if request.POST.get('check180'):
                score+=num[179]
            if request.POST.get('check181'):
                score+=num[180]
            if request.POST.get('check182'):
                score+=num[181]
            if request.POST.get('check183'):
                score+=num[182]
            if request.POST.get('check184'):
                score+=num[183]
            if request.POST.get('check185'):
                score+=num[184]
            if request.POST.get('check186'):
                score+=num[185]
            if request.POST.get('check187'):
                score+=num[186]
            if request.POST.get('check188'):
                score+=num[187]
            if request.POST.get('check189'):
                score+=num[188]
            if request.POST.get('check190'):
                score+=num[189]
            if request.POST.get('check191'):
                score+=num[190]
            if request.POST.get('check192'):
                score+=num[191]
            if request.POST.get('check193'):
                score+=num[192]
            if request.POST.get('check194'):
                score+=num[193]
            if request.POST.get('check195'):
                score+=num[194]
            if request.POST.get('check196'):
                score+=num[195]
            if request.POST.get('check197'):
                score+=num[196]
            if request.POST.get('check198'):
                score+=num[197]
            if request.POST.get('check199'):
                score+=num[198]
            if request.POST.get('check200'):
                score+=num[199]
            if request.POST.get('check201'):
                score+=num[200]
            if request.POST.get('check202'):
                score+=num[201]
            if request.POST.get('check203'):
                score+=num[202]
            if request.POST.get('check204'):
                score+=num[203]
            if request.POST.get('check205'):
                score+=num[204]
            if request.POST.get('check206'):
                score+=num[205]
            if request.POST.get('check207'):
                score+=num[206]
            if request.POST.get('check208'):
                score+=num[207]
            if request.POST.get('check209'):
                score+=num[208]
            if request.POST.get('check210'):
                score+=num[209]
            if request.POST.get('check211'):
                score+=num[210]
            if request.POST.get('check212'):
                score+=num[211]
            if request.POST.get('check213'):
                score+=num[212]
            if request.POST.get('check214'):
                score+=num[213]
            if request.POST.get('check215'):
                score+=num[214]
            if request.POST.get('check216'):
                score+=num[215]
            if request.POST.get('check217'):
                score+=num[216]
            if request.POST.get('check218'):
                score+=num[217]
            if request.POST.get('check219'):
                score+=num[218]
            if request.POST.get('check220'):
                score+=num[219]
            if request.POST.get('check221'):
                score+=num[220]
            if request.POST.get('check222'):
                score+=num[221]
            if request.POST.get('check223'):
                score+=num[222]
            if request.POST.get('check224'):
                score+=num[223]
            if request.POST.get('check225'):
                score+=num[224]
            if request.POST.get('check226'):
                score+=num[225]
            if request.POST.get('check227'):
                score+=num[226]
            if request.POST.get('check228'):
                score+=num[227]
            if request.POST.get('check229'):
                score+=num[228]
            if request.POST.get('check230'):
                score+=num[229]
            if request.POST.get('check231'):
                score+=num[230]
            if request.POST.get('check232'):
                score+=num[231]
            if request.POST.get('check233'):
                score+=num[232]
            if request.POST.get('check234'):
                score+=num[233]
            if request.POST.get('check235'):
                score+=num[234]
            if request.POST.get('check236'):
                score+=num[235]
            if request.POST.get('check237'):
                score+=num[236]
            if request.POST.get('check238'):
                score+=num[237]
            if request.POST.get('check239'):
                score+=num[238]
            if request.POST.get('check240'):
                score+=num[239]
            if request.POST.get('check241'):
                score+=num[240]
            if request.POST.get('check242'):
                score+=num[241]
            if request.POST.get('check243'):
                score+=num[242]
            if request.POST.get('check244'):
                score+=num[243]
            if request.POST.get('check245'):
                score+=num[244]
            if request.POST.get('check246'):
                score+=num[245]
            if request.POST.get('check247'):
                score+=num[246]
            if request.POST.get('check248'):
                score+=num[247]
            if request.POST.get('check249'):
                score+=num[248]
            if request.POST.get('check250'):
                score+=num[249]
            if request.POST.get('check251'):
                score+=num[250]
            if request.POST.get('check252'):
                score+=num[251]
            if request.POST.get('check253'):
                score+=num[252]
            if request.POST.get('check254'):
                score+=num[253]
            if request.POST.get('check255'):
                score+=num[254]
            if request.POST.get('check256'):
                score+=num[255]
            if request.POST.get('check257'):
                score+=num[256]
            if request.POST.get('check258'):
                score+=num[257]
            if request.POST.get('check259'):
                score+=num[258]
            if request.POST.get('check260'):
                score+=num[259]
            if request.POST.get('check261'):
                score+=num[260]
            if request.POST.get('check262'):
                score+=num[261]
            if request.POST.get('check263'):
                score+=num[262]
            if request.POST.get('check264'):
                score+=num[263]
            if request.POST.get('check265'):
                score+=num[264]
            if request.POST.get('check266'):
                score+=num[265]
            if request.POST.get('check267'):
                score+=num[266]
            if request.POST.get('check268'):
                score+=num[267]
            if request.POST.get('check269'):
                score+=num[268]
            if request.POST.get('check270'):
                score+=num[269]
            if request.POST.get('check271'):
                score+=num[270]
            if request.POST.get('check272'):
                score+=num[271]
            if request.POST.get('check273'):
                score+=num[272]
            if request.POST.get('check274'):
                score+=num[273]
        print('score',score)
        pscore = score/10
        fms = pow(10, (-0.02 * pscore + 1))
        faci.managementfactor = roundData.roundDF(fms)
        faci.save()
        return redirect('facilitiesEdit', facilityID=facilityID)
    return render(request, 'FacilityUI/equipment/ManagementSystems.html',
                  {'page': 'mana', 'facilityID': facilityID, 'siteID': faci.siteid_id, 'count': count,
                   'info': request.session, 'noti': noti, 'countnoti': countnoti})

def RegularVerification():
    # print(1)
    obj = REGULAR()
    obj.regular_1()
def signin(request):
    error = ''
    try:
        # t1 = threading.Thread(target=RegularVerification)
        # t1.setDaemon(True)
        # t1.start()
        # t2 = threading.Thread(target=subscribe.SubDATA)
        # t2.setDaemon(True)
        # t2.start()
        if request.session.has_key('id'):
            if request.session['kind'] == 'citizen':
                return redirect('citizenHome')
            elif request.session['kind'] == 'factory':
                facilityID1 = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
                return redirect('facilitiesDisplay', facilityID1)
            elif request.session['kind'] == 'manager':
                return redirect('manager', 3)
        else:
            if request.method == 'POST':
                xuser = request.POST.get('txtuser')
                xpass = request.POST.get('txtpass')
                data = models.ZUser.objects.filter(Q(username=xuser), Q(password=xpass), Q(active=1))
                if data.count():
                    request.session['id'] = data[0].id
                    request.session['name'] = data[0].name
                    request.session['kind'] = data[0].kind
                    request.session['phone'] = data[0].phone
                    request.session['address'] = data[0].adress
                    request.session['email'] = data[0].email
                    request.session['other_info'] = data[0].other_info
                    request.session.set_expiry(0)
                    if request.session['kind'] == 'citizen':
                        return redirect('citizenHome')
                    elif request.session['kind'] == 'factory':
                        facilityID = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
                        return redirect('facilitiesDisplay', facilityID)
                    else:
                        return redirect('managerhomedetail', 3)
                else:
                    error = "Tài khoản hoặc mật khẩu không đúng"
            return render(request, 'Home/index.html', {'error': error})
    except Exception as e:
        print(e)
        raise Http404


def logout(request):
    try:
        del request.session['id']
        request.session.flush()
    except:
        pass
    return redirect('home')


################## Forum Dien Dan ###################
def base_forum(request):
    countveri = 0
    if request.session.has_key('id'):
        if 'btnsend' in request.POST:
            xtitle = request.POST.get('txttitle')
            xcontent = request.POST.get('txtcontent')
            xtag = request.POST.get('txttag')
            a = models.ZPosts(title=xtitle, tag=xtag, content=xcontent, time=datetime.now(),
                              id_user=request.session['id'], views=0)
            a.save()
        mang = []
        data = models.ZPosts.objects.all()
        for dataposts in data:
            posts = {}
            posts['id'] = dataposts.id
            posts['id_user'] = dataposts.id_user
            posts['title'] = dataposts.title
            posts['content'] = dataposts.content
            posts['time'] = dataposts.time
            posts['tag'] = dataposts.tag
            posts['views'] = dataposts.views
            posts['reply'] = models.ZComment.objects.all().filter(id_posts=dataposts.id).count()
            mang.append(posts)
        if request.session.has_key('kind') == "factory":
            siteid = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
            faci = models.Facility.objects.get(siteid=siteid)
            countveri = models.Verification.objects.filter(facility=faci.facilityid).filter(Is_active=0).count()
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        return render(request, 'BaseUI/BaseForum/forumhome.html',
                      {'data': mang, 'noti': noti, 'countnoti': countnoti,'countveri':countveri,'count':count ,'info': request.session})
    else:
        return redirect('home')


def posts_forum(request, postID):
    a = models.ZPosts.objects.filter(id=postID)[0]
    a.views += 1
    a.save()
    nameuserpost = models.ZUser.objects.all().filter(id=a.id_user)[0].name
    countveri = 0
    if request.session['id'] == a.id_user:
        noti = models.ZNotification.objects.all().filter(link=postID)
        for notifi in noti:
            notifi.state = 1
            notifi.save()
    if 'btncomment' in request.POST:
        xcontent = request.POST.get('txtcomment')
        data = models.ZComment(content=xcontent, time=datetime.now(), id_posts=postID, id_user=request.session['id'])
        data.save()  # Thêm thông tin comment vào csdl
        # chức năng thông báo
        id_user = models.ZPosts.objects.all().filter(id=postID)[0].id_user  # Lấy ID người đăng bài
        title_post = models.ZPosts.objects.all().filter(id=postID)[0].title
        if request.session['id'] != id_user:
            noti = models.ZNotification(id_user=id_user, subject=request.session['name'],
                                        content=' đã phản hồi bài viết ', object=title_post, link=postID,
                                        time=datetime.now(), state=0)
            noti.save()

    comment = models.ZComment.objects.all().filter(id_posts=postID)  # Lấy dữ liệu comment của this post
    datacmt = []
    for data in comment:
        cmt = {}
        cmt['name'] = models.ZUser.objects.all().filter(id=data.id_user)[0].name
        cmt['content'] = data.content
        datacmt.append(cmt)  # mang chua Du lieu cac comment
    # if request.session.kind == 'factory':
    #     siteid = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
    #     faci = models.Facility.objects.get(siteid=siteid)
    #     countveri = models.Verification.objects.filter(facility=faci.facilityid).filter(Is_active=0).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'BaseUI/BaseForum/forumposts.html',
                  {'data': a, 'nameuserpost': nameuserpost, 'datacmt': datacmt, 'session': request.session,
                   'noti': noti, 'countnoti': countnoti, 'info': request.session})


################## Tin nhan Email ###################
def MessagesInbox(request):
    datacontent = models.Emailto.objects.filter(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email)
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    countveri = 0
    try:
        if 'post' in request.POST:
            data = {}
            data['emailto'] = request.POST.get('sentto')
            data['subject'] = request.POST.get('subject')
            data['emailsent'] = models.ZUser.objects.filter(id=request.session['id'])[0].email
            data['content'] = request.POST.get('content')
            a = models.Emailsent(content=data['content'], subject=data['subject'], Emails=data['emailsent'],
                                 Emailt=data['emailto'])
            a.save()
            b = models.Emailto(content=data['content'], subject=data['subject'], Emails=data['emailsent'],
                               Emailt=data['emailto'], Is_see=0)
            b.save()
        if request.method == 'POST':
            for data1 in datacontent:
                if request.POST.get('%d' % data1.id):
                    email1 = models.Emailto.objects.get(id=data1.id)
                    email1.delete()
                    return redirect('messagesInbox')
        acti = models.Emailto.objects.filter(Emailt=request.session['email'])
        if request.session.has_key('kind') == 'factory':
            siteid = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
            faci = models.Facility.objects.get(siteid=siteid)
            countveri = models.Verification.objects.filter(facility=faci.facilityid).filter(Is_active=0).count()
        for acti in acti:
            acti.Is_see = 1
            acti.save()
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'Messages/Messages_Inbox.html',
                  {'page': 'messagesInbox', 'datacontent': datacontent, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def Email_Message_sent(request):
    datacontent = models.Emailsent.objects.filter(Emails=models.ZUser.objects.filter(id=request.session['id'])[0].email)
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    countveri = 0
    try:
        if 'post' in request.POST:
            data = {}
            data['emailto'] = request.POST.get('sentto')
            data['subject'] = request.POST.get('subject')
            data['emailsent'] = models.ZUser.objects.filter(id=request.session['id'])[0].email
            data['content'] = request.POST.get('content')
            a = models.Emailsent(content=data['content'], subject=data['subject'], Emails=data['emailsent'],
                                 Emailt=data['emailto'])
            a.save()
            b = models.Emailto(content=data['content'], subject=data['subject'], Emails=data['emailsent'],
                               Emailt=data['emailto'], Is_see=0)
            b.save()
        if request.method == 'POST':
            for data1 in datacontent:
                if request.POST.get('%d' % data1.id):
                    email1 = models.Emailsent.objects.get(id=data1.id)
                    email1.delete()
                    return redirect('messagesSent')
        if request.session.has_key('kind') == 'factory':
            siteid = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
            faci = models.Facility.objects.get(siteid=siteid)
            countveri = models.Verification.objects.filter(facility=faci.facilityid).filter(Is_active=0).count()
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'Messages/Messages_Sent.html',
                  {'page': 'messagesSent', 'datacontent': datacontent, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


################# Help #################
def Help(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/help.html',
                  {'page': 'home', 'info': request.session, 'count': count, 'noti': noti, 'countnoti': countnoti,
                   'countveri': countveri})


def Help_Usermanual_Citizen(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/User_Manual/help_Citizen.html',
                  {'page': 'userManual', 'info': request.session, 'count': count, 'noti': noti, 'countnoti': countnoti})


def Help_Usermanual_Business(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/User_Manual/help_Business.html',
                  {'page': 'userManual', 'info': request.session, 'count': count, 'noti': noti, 'countnoti': countnoti})


def Help_Usermanual_Manager(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/User_Manual/help_Manager.html',
                  {'page': 'userManual', 'info': request.session, 'count': count, 'noti': noti, 'countnoti': countnoti})


def Help_AccountManagement_LoginPass(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Account_Management/Login_and_Password.html',
                  {'page': 'accountManager', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


def Help_AccountManagement_PerInfo(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Account_Management/Personal_Information.html',
                  {'page': 'accountManager', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


def Help_AccountManagement_AccessDownload(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Account_Management/Access_and_Download_Information.html',
                  {'page': 'accountManager', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


def Help_AccountManagement_Notification(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Account_Management/Notification.html',
                  {'page': 'accountManager', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


def Policies_Reports(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Policies_Reports.html',
                  {'page': 'policiesReports', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


def Private_Safe(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/Private_Safe.html',
                  {'page': 'privateSafe', 'info': request.session, 'count': count, 'noti': noti,
                   'countnoti': countnoti})


################ Dang ki tai khoan ####################
def AccountCitizen(request):
    infor = {}
    try:
        if request.method == "POST":
            user = request.POST.get('username')
            name = request.POST.get('name')
            # last_name = request.POST.get('txtlname')
            password = request.POST.get('txtpass')
            repassword = request.POST.get('repass')
            phone = request.POST.get('txtmobile')
            email = request.POST.get('txtmail')
            addr = request.POST.get('txtadd')
            kind = 'citizen'
            desc = request.POST.get('CompanyInformation')
            # print(companyName + " " + user + " " + email)
            if password == repassword:
                authUser = models.ZUser.objects.filter(Q(username=user) | Q(email=email))
                if authUser.count() > 0:
                    infor['exist'] = "This User Name or E-mail was taken"
                    print(infor['exist'])
                else:
                    try:
                        authUser1 = models.ZUser(username=user, phone=phone, adress=addr, email=email, name=name,
                                                 kind=kind, password=password)
                        authUser1.save()
                        print(authUser1.username)
                        # profile = models.ZProfilebisiness(user_id=authUser1.id, organization_detail=desc)
                        # profile.save()
                    except Exception as e:
                        print(e)
                    current_site = get_current_site(request)
                    print("a")
                    email_subject = "Activate your block account"
                    message = render_to_string('Home/Account/activateEmail.html', {
                        'user': authUser1,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(authUser1.pk)).decode(),
                        'token': gen_token.make_token(authUser1)
                    })
                    print('ok')
                    to_email = email
                    Email = EmailMessage(email_subject, message, to=[to_email])
                    Email.send()
                    print("sended")
                    # return HttpResponse("Please confirm in your e-mail")
                    return render_to_response('response/complete_regiatration.html')
            else:
                infor['match'] = "The password is not match"
    except Exception as e:
        print(e)
    return render(request, 'Home/Account/sigup_citizen.html')


def AccountBusiness(request):
    infor = {}
    try:
        if request.method == "POST":
            companyName = request.POST.get('companyname_business')
            user = request.POST.get('username')
            # first_name = request.POST.get('first_name')
            # last_name = request.POST.get('last_name')
            name = request.POST.get('name')
            password = request.POST.get('password')
            repassword = request.POST.get('repassword')
            phone = request.POST.get('phone')
            email = request.POST.get('txtmail')
            addr = request.POST.get('txtadd')
            kind = 'factory'
            desc = request.POST.get('CompanyInformation')
            print(companyName + " " + user + " " + email)
            if password == repassword:
                authUser = models.ZUser.objects.filter(Q(username=user) | Q(email=email))
                print("ok")
                if authUser.count() > 0:
                    infor['exist'] = "This User Name or E-mail was taken"
                    print(infor['exist'])
                else:
                    try:
                        authUser1 = models.ZUser(username=user, phone=phone, adress=addr, email=email, name=name,
                                                 kind=kind, password=password)
                        authUser1.save()
                        print(authUser1.username)
                        fa = models.Sites(sitename=companyName, userID_id=authUser1.id)
                        fa.save()
                        bu = models.Zbusiness(compainfor=desc, namecompany=companyName, userID_id=authUser1.id)
                        bu.save()
                    except Exception as e:
                        print(e)
                    current_site = get_current_site(request)
                    print("a")
                    email_subject = "Activate your block account"
                    message = render_to_string('Home/Account/activateEmail.html', {
                        'user': authUser1,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(authUser1.pk)).decode(),
                        'token': gen_token.make_token(authUser1)
                    })
                    print('ok')
                    to_email = email
                    Email = EmailMessage(email_subject, message, to=[to_email])
                    Email.send()
                    print("sended")
                    # return HttpResponse("Please confirm in your e-mail")
                    return render_to_response('response/complete_regiatration.html')
            else:
                infor['match'] = "The password is not match"
    except Exception as e:
        print(e)
    return render(request, 'Home/Account/signup_business.html')


def AccountManagement(request):
    infor = {}
    try:
        if request.method == "POST":
            org_name = request.POST.get('org_name_mng')
            user = request.POST.get('username_mng')
            # first_name = request.POST.get('first_name')
            # last_name = request.POST.get('last_name')
            name = request.POST.get('name')
            password = request.POST.get('pass_mng')
            repassword = request.POST.get('repass_mng')
            phone = request.POST.get('phone_mng')
            email = request.POST.get('email_mng')
            addr = request.POST.get('addr_mng')
            web = request.POST.get('web_mng')
            desc = request.POST.get('desc')
            kind = 'manager'
            print(org_name + " " + user + " " + email)
            if password == repassword:
                authUser = models.ZUser.objects.filter(Q(username=user) | Q(email=email))
                print("ok")
                if authUser.count() > 0:
                    infor['exist'] = "This User Name or E-mail was taken"
                    print(infor['exist'])
                else:
                    try:
                        authUser1 = models.ZUser(username=user, phone=phone, adress=addr, email=email, name=name,
                                                 kind=kind, password=password)
                        authUser1.save()
                        print(authUser1.username)
                        # profile = models.ZProfilebisiness(user_id=authUser1.id, organization_detail=desc)
                        # profile.save()
                    except Exception as e:
                        print(e)
                    current_site = get_current_site(request)
                    print("a")
                    email_subject = "Activate your block account"
                    message = render_to_string('Home/Account/activateEmail.html', {
                        'user': authUser1,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(authUser1.pk)).decode(),
                        'token': gen_token.make_token(authUser1)
                    })
                    print('ok')
                    to_email = email
                    Email = EmailMessage(email_subject, message, to=[to_email])
                    Email.send()
                    print("sended")
                    # return HttpResponse("Please confirm in your e-mail")
                    return render_to_response('response/complete_regiatration.html')
            else:
                infor['match'] = "The password is not match"
    except Exception as e:
        print(e)
    return render(request, 'Home/Account/signup_management.html')


def activate(request, uidb64, token):
    try:
        # uid = force_text(urlsafe_base64_decode(uidb64))
        uid = urlsafe_base64_decode(uidb64).decode()
        user = models.ZUser.objects.get(pk=uid)
        print("1")
    except(TypeError, ValueError, OverflowError, models.ZUser.DoesNotExist):
        user = None
    print(gen_token.check_token(user, token))
    print("2")
    if user is not None and gen_token.check_token(user, token):
        user.active = True
        user.save()
        # login(request, user)
        # return HttpResponse("Activate is complete! Thanks for use our services")
        print("aaaaaa")
        return render_to_response('response/totally_complete.html')
    else:
        print(user.username)
        return HttpResponse("Can't activate now, please try again later or contact us")


################ Manager UI Control ###################
def ManagerHomeDetail(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'ManagerUI/Home_Manager.html',
                  {'page': 'managerHomeDetail', 'siteID': siteID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


# NOTE: page: managerHomeDetail dùng cho baseMN khi so sanh, khác với name: managerhomedetail trong view
# def CalculateFunctionManager(request, siteID):
#     noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
#     countnoti = noti.filter(state=0).count()
#     count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
#                                           Q(Is_see=0)).count()
#     # data = ListNormalProposalFofInpsection(siteID=siteID, facilityID=0, equimentID=0)
#     # dataTank = ListTankProposalForInpsection(siteID=siteID, facilityID=0, equimentID=0)
#     return render(request, 'ManagerUI/Calculate_Function_Manager.html',
#                   {'page': 'calculateFunctionManager', 'siteID': siteID, 'info': request.session, 'noti': noti,
#                    'countnoti': countnoti, 'count': count})


def ToolManager(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'ManagerUI/Tool_Manager.html',
                  {'page': 'toolManager', 'siteID': siteID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def ManagerHome(request, siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    try:
        risk = []

        data = models.Sites.objects.all()
        for a in data:
            dataF = {}
            dataF['ID'] = a.siteid
            dataF['CreatedTime'] = a.create
            dataF['SideName'] = a.sitename
            risk.append(dataF)
        pagiFaci = Paginator(risk, 25)
        pageFaci = request.GET.get('page', 1)
        try:
            users = pagiFaci.page(pageFaci)
        except PageNotAnInteger:
            users = pagiFaci.page(1)
        except EmptyPage:
            users = pageFaci.page(pagiFaci.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/Business_List.html',
                  {'page': 'listManagement', 'obj': users, 'siteID': siteID, 'count': count, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})


def ListFacilitiesMana(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        risk = []
        si = models.Sites.objects.get(siteid=siteID)
        data = models.Facility.objects.filter(siteid=siteID)
        # print(data.site_id)
        # si=models.Sites.objects.get(siteid=data.siteid_id)
        for a in data:
            dataF = {}
            risTarget = models.FacilityRiskTarget.objects.get(facilityid=a.facilityid)
            dataF['ID'] = a.facilityid
            dataF['CreatedTime'] = a.create
            dataF['FacilitiName'] = a.facilityname
            dataF['ManagementFactor'] = a.managementfactor
            dataF['RiskTarget'] = risTarget.risktarget_fc
            risk.append(dataF)

        pagiFaci = Paginator(risk, 25)
        pageFaci = request.GET.get('page', 1)
        try:
            users = pagiFaci.page(pageFaci)
        except PageNotAnInteger:
            users = pagiFaci.page(1)
        except EmptyPage:
            users = pageFaci.page(pagiFaci.num_pages)
        noti = models.ZNotification.objects.filter(link=siteID)
        for notifi in noti:
            if request.session['id'] == notifi.id_user:
                notifi.state = 1
                notifi.save()
    except:
        raise Http404
    return render(request, 'ManagerUI/facility_List.html',
                  {'page': 'listFacility', 'obj': users, 'siteID': siteID, 'count': count, 'si': si, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})


def ListEquipmentMana(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        faci = models.Facility.objects.get(facilityid=facilityID)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        data = models.EquipmentMaster.objects.filter(facilityid=facilityID)
        pagiEquip = Paginator(data, 25)
        pageEquip = request.GET.get('page', 1)
        try:
            obj = pagiEquip.page(pageEquip)
        except PageNotAnInteger:
            obj = pagiEquip.page(1)
        except EmptyPage:
            obj = pageEquip.page(pagiEquip.num_pages)
        noti = models.ZNotification.objects.filter(link=facilityID)
        for notifi in noti:
            if request.session['id'] == notifi.id_user:
                notifi.state = 1
                notifi.save()
    except:
        raise Http404
    return render(request, 'ManagerUI/Equipment_List.html',
                  {'page': 'listEquip', 'obj': obj, 'facilityID': facilityID, 'siteID': faci.siteid_id, 'faci': faci,
                   'si': si, 'count': count, 'noti': noti, 'countnoti': countnoti, 'info': request.session})


def ListComponentMana(request, equipmentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        eq = models.EquipmentMaster.objects.get(equipmentid=equipmentID)
        faci = models.Facility.objects.get(facilityid=eq.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        data = models.ComponentMaster.objects.filter(equipmentid=equipmentID)
        pagiComp = Paginator(data, 25)
        pageComp = request.GET.get('page', 1)
        print("hihihihihihihihi")
        print(faci.siteid_id)
        try:
            obj = pagiComp.page(pageComp)
        except PageNotAnInteger:
            obj = pagiComp.page(1)
        except EmptyPage:
            obj = pageComp.page(pagiComp.num_pages)
        noti = models.ZNotification.objects.filter(link=equipmentID)
        for notifi in noti:
            if request.session['id'] == notifi.id_user:
                notifi.state = 1
                notifi.save()
    except:
        raise Http404
    return render(request, 'ManagerUI/component_List.html',
                  {'page': 'listComp', 'obj': obj, 'equipmentID': equipmentID, 'facilityID': eq.facilityid_id,
                   'siteID': faci.siteid_id, 'eq': eq, 'faci': faci, 'si': si, 'count': count, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})


def ListManufactureMana(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        data = models.Manufacturer.objects.filter(siteid=siteID)
        pagiManu = Paginator(data, 25)
        pageManu = request.GET.get('page', 1)
        try:
            obj = pagiManu.page(pageManu)
        except PageNotAnInteger:
            obj = pagiManu.page(1)
        except EmptyPage:
            obj = pageManu.page(pagiManu.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/manufacture_List.html',
                  {'page': 'listManu', 'obj': obj, 'siteID': siteID, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def ListProposalMana(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwass = models.RwAssessment.objects.filter(componentid=componentID)
        data = []
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        tank = [8, 12, 14, 15]
        for a in rwass:
            df = models.RwFullPof.objects.filter(id=a.id)
            fc = models.RwFullFcof.objects.filter(id=a.id)
            dm = models.RwDamageMechanism.objects.filter(id_dm=a.id)
            obj1 = {}
            obj1['id'] = a.id
            obj1['name'] = a.proposalname
            obj1['lastinsp'] = a.assessmentdate.strftime('%Y-%m-%d')
            if df.count() != 0:
                obj1['df'] = round(df[0].totaldfap1, 2)
                obj1['gff'] = df[0].gfftotal
                obj1['fms'] = df[0].fms
            else:
                obj1['df'] = 0
                obj1['gff'] = 0
                obj1['fms'] = 0
            if fc.count() != 0:
                obj1['fc'] = round(fc[0].fcofvalue, 2)
            else:
                obj1['fc'] = 0
            if dm.count() != 0:
                obj1['duedate'] = dm[0].inspduedate.date().strftime('%Y-%m-%d')
            else:
                obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=15)).strftime('%Y-%m-%d')
                obj1['lastinsp'] = equip.commissiondate.date().strftime('%Y-%m-%d')
            obj1['risk'] = round(obj1['df'] * obj1['gff'] * obj1['fms'] * obj1['fc'], 2)
            data.append(obj1)
        pagidata = Paginator(data, 25)
        pagedata = request.GET.get('page', 1)
        try:
            obj = pagidata.page(pagedata)
        except PageNotAnInteger:
            obj = pagidata.page(1)
        except EmptyPage:
            obj = pagedata.page(pagidata.num_pages)

        if comp.componenttypeid_id in tank:
            istank = 1
        else:
            istank = 0
        if comp.componenttypeid_id == 8 or comp.componenttypeid_id == 14:
            isshell = 1
        else:
            isshell = 0
    except:
        raise Http404
    return render(request, 'ManagerUI/proposal_List.html',
                  {'page': 'listProposal', 'obj': obj, 'istank': istank, 'isshell': isshell,
                   'facilityID': equip.facilityid_id, 'componentID': componentID, 'siteID': faci.siteid_id,
                   'equipmentID': comp.equipmentid_id, 'comp': comp, 'equip': equip, 'faci': faci, 'si': si,
                   'count': count, 'noti': noti, 'countnoti': countnoti, 'info': request.session})


def ListDesignCodeMana(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        data = models.DesignCode.objects.filter(siteid=siteID)
        pagiDes = Paginator(data, 25)
        pageDes = request.GET.get('page', 1)
        try:
            obj = pagiDes.page(pageDes)
        except PageNotAnInteger:
            obj = pagiDes.page(1)
        except EmptyPage:
            obj = pageDes.page(pagiDes.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/designcode_List.html',
                  {'page': 'listDesign', 'obj': obj, 'siteID': siteID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})


def FullyDamageFactorMana(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        df = models.RwFullPof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        data = {}
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        siteID = equip.siteid_id
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        data['thinningType'] = df.thinningtype
        data['gfftotal'] = df.gfftotal
        data['fms'] = df.fms
        data['thinningap1'] = roundData.roundDF(df.thinningap1)
        data['thinningap2'] = roundData.roundDF(df.thinningap2)
        data['thinningap3'] = roundData.roundDF(df.thinningap3)
        data['sccap1'] = roundData.roundDF(df.sccap1)
        data['sccap2'] = roundData.roundDF(df.sccap2)
        data['sccap3'] = roundData.roundDF(df.sccap3)
        data['externalap1'] = roundData.roundDF(df.externalap1)
        data['externalap2'] = roundData.roundDF(df.externalap2)
        data['externalap3'] = roundData.roundDF(df.externalap3)
        data['htha_ap1'] = roundData.roundDF(df.htha_ap1)
        data['htha_ap2'] = roundData.roundDF(df.htha_ap2)
        data['htha_ap3'] = roundData.roundDF(df.htha_ap3)
        data['brittleap1'] = roundData.roundDF(df.brittleap1)
        data['brittleap2'] = roundData.roundDF(df.brittleap2)
        data['brittleap3'] = roundData.roundDF(df.brittleap3)
        data['fatigueap1'] = roundData.roundDF(df.fatigueap1)
        data['fatigueap2'] = roundData.roundDF(df.fatigueap2)
        data['fatigueap3'] = roundData.roundDF(df.fatigueap3)
        data['thinninggeneralap1'] = roundData.roundDF(df.thinninggeneralap1)
        data['thinninggeneralap2'] = roundData.roundDF(df.thinninggeneralap2)
        data['thinninggeneralap3'] = roundData.roundDF(df.thinninggeneralap3)
        data['thinninglocalap1'] = roundData.roundDF(df.thinninglocalap1)
        data['thinninglocalap2'] = roundData.roundDF(df.thinninglocalap2)
        data['thinninglocalap3'] = roundData.roundDF(df.thinninglocalap3)
        data['totaldfap1'] = roundData.roundDF(df.totaldfap1)
        data['totaldfap2'] = roundData.roundDF(df.totaldfap2)
        data['totaldfap3'] = roundData.roundDF(df.totaldfap3)
        data['pofap1'] = roundData.roundPoF(df.pofap1)
        data['pofap2'] = roundData.roundPoF(df.pofap2)
        data['pofap3'] = roundData.roundPoF(df.pofap3)
        data['pofap1category'] = df.pofap1category
        data['pofap2category'] = df.pofap2category
        data['pofap3category'] = df.pofap3category
        if request.method == 'POST':
            df.thinningtype = request.POST.get('thinningType')
            df.save()
            ReCalculate.ReCalculate(proposalID)
            return redirect('veridamgeFactorMana', proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'ManagerUI/RiskSummaryMana/FullDF.html',
                  {'page': 'damageFactor', 'obj': data, 'assess': rwAss, 'isTank': isTank, 'siteID': siteID,
                   'isShell': isShell, 'proposalID': proposalID, 'count': count, 'noti': noti, 'countnoti': countnoti,
                   'info': request.session})


def FullyConsequenceMana(request, proposalID):
    data = {}
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        siteID = equip.siteid_id
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        if isBottom:
            bottomConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['hydraulic_water'] = roundData.roundFC(bottomConsequences.hydraulic_water)
            data['hydraulic_fluid'] = roundData.roundFC(bottomConsequences.hydraulic_fluid)
            data['seepage_velocity'] = roundData.roundFC(bottomConsequences.seepage_velocity)
            data['flow_rate_d1'] = roundData.roundFC(bottomConsequences.flow_rate_d1)
            data['flow_rate_d4'] = roundData.roundFC(bottomConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(bottomConsequences.leak_duration_d1)
            data['leak_duration_d4'] = roundData.roundFC(bottomConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(bottomConsequences.release_volume_leak_d1)
            data['release_volume_leak_d4'] = roundData.roundFC(bottomConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(bottomConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(bottomConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(bottomConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(bottomConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(bottomConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(bottomConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(bottomConsequences.fc_environ)
            data['material_factor'] = bottomConsequences.material_factor
            data['component_damage_cost'] = roundData.roundMoney(bottomConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(bottomConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(bottomConsequences.consequence)
            data['consequencecategory'] = bottomConsequences.consequencecategory
            if request.method == 'POST':
                return redirect('verifullyConsequenceMana', proposalID)
            return render(request, 'ManagerUI/RiskSummaryMana/fullyBottomConsequenceMana.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session})
        elif isShell:
            shellConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['flow_rate_d1'] = roundData.roundFC(shellConsequences.flow_rate_d1)
            data['flow_rate_d2'] = roundData.roundFC(shellConsequences.flow_rate_d2)
            data['flow_rate_d3'] = roundData.roundFC(shellConsequences.flow_rate_d3)
            data['flow_rate_d4'] = roundData.roundFC(shellConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(shellConsequences.leak_duration_d1)
            data['leak_duration_d2'] = roundData.roundFC(shellConsequences.leak_duration_d2)
            data['leak_duration_d3'] = roundData.roundFC(shellConsequences.leak_duration_d3)
            data['leak_duration_d4'] = roundData.roundFC(shellConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(shellConsequences.release_volume_leak_d1)
            data['release_volume_leak_d2'] = roundData.roundFC(shellConsequences.release_volume_leak_d2)
            data['release_volume_leak_d3'] = roundData.roundFC(shellConsequences.release_volume_leak_d3)
            data['release_volume_leak_d4'] = roundData.roundFC(shellConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(shellConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(shellConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(shellConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(shellConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(shellConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(shellConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(shellConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(shellConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(shellConsequences.fc_environ)
            data['component_damage_cost'] = roundData.roundMoney(shellConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(shellConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(shellConsequences.consequence)
            data['consequencecategory'] = shellConsequences.consequencecategory
            if request.method == 'POST':
                return redirect('verifullyConsequenceMana', proposalID)
            return render(request, 'ManagerUI/RiskSummaryMana/fullyShellConsequenceMana.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session})
        else:
            print(" vào thiết bị thường")
            ca = models.RwCaLevel1.objects.get(id=proposalID)
            inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
            data['production_cost'] = roundData.roundMoney(inputCa.production_cost)
            data['equipment_cost'] = roundData.roundMoney(inputCa.equipment_cost)
            data['personal_density'] = inputCa.personal_density
            data['evironment_cost'] = roundData.roundMoney(inputCa.evironment_cost)
            data['ca_cmd'] = roundData.roundFC(ca.ca_cmd)
            data['ca_inj_flame'] = roundData.roundFC(ca.ca_inj_flame)
            data['fc_cmd'] = roundData.roundMoney(ca.fc_cmd)
            data['fc_affa'] = roundData.roundMoney(ca.fc_affa)
            data['fc_prod'] = roundData.roundMoney(ca.fc_prod)
            data['fc_inj'] = roundData.roundMoney(ca.fc_inj)
            data['fc_envi'] = roundData.roundMoney(ca.fc_envi)
            data['fc_total'] = roundData.roundMoney(ca.fc_total)
            data['fcof_category'] = ca.fcof_category
            print("lấy xong dữ liệu")
            if request.method == 'POST':
                print("vào method post")
                return redirect('verifullyConsequenceMana', proposalID)
            return render(request, 'ManagerUI/RiskSummaryMana/fullyNormalConsequenceMana.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session, 'siteID': siteID})
    except Exception as e:
        print(e)
        raise Http404


def RiskChartMana(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwAssessment = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAssessment.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        siteID = equip.siteid_id
        rwFullpof = models.RwFullPof.objects.get(id=proposalID)
        rwFullcof = models.RwFullFcof.objects.get(id=proposalID)
        risk = rwFullpof.pofap1 * rwFullcof.fcofvalue
        chart = models.RwDataChart.objects.get(id=proposalID)
        assessmentDate = rwAssessment.assessmentdate
        dataChart = [risk, chart.riskage1, chart.riskage2, chart.riskage3, chart.riskage4, chart.riskage5,
                     chart.riskage6,
                     chart.riskage7, chart.riskage8, chart.riskage9, chart.riskage9, chart.riskage10, chart.riskage11,
                     chart.riskage12, chart.riskage13, chart.riskage14, chart.riskage15]
        dataLabel = [date2Str.date2str(assessmentDate), date2Str.date2str(date2Str.dateFuture(assessmentDate, 1)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 2)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 3)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 4)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 5)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 6)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 7)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 8)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 9)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 10)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 11)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 12)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 13)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 14))]
        dataTarget = [chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget]
        endLabel = date2Str.date2str(date2Str.dateFuture(assessmentDate, 15))
        content = {'page': 'riskChart', 'label': dataLabel, 'data': dataChart, 'target': dataTarget,
                   'endLabel': endLabel, 'proposalname': rwAssessment.proposalname,
                   'proposalID': rwAssessment.id, 'componentID': rwAssessment.componentid_id, 'count': count,
                   'noti': noti, 'countnoti': countnoti, 'info': request.session, 'siteID': siteID}
        return render(request, 'ManagerUI/RiskSummaryMana/riskChartMana.html', content)
    except:
        raise Http404


def RiskMatrixMana(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    rwAss = models.RwAssessment.objects.get(id=proposalID)
    component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
    equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
    siteID = equip.siteid_id
    try:
        locatAPI1 = {}
        locatAPI2 = {}
        locatAPI3 = {}
        locatAPI1['x'] = 0
        locatAPI1['y'] = 500

        locatAPI2['x'] = 0
        locatAPI2['y'] = 500

        locatAPI3['x'] = 0
        locatAPI3['y'] = 500

        df = models.RwFullPof.objects.get(id=proposalID)
        ca = models.RwFullFcof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0

        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        Ca = round(ca.fcofvalue, 2)
        DF1 = round(df.totaldfap1, 2)
        DF2 = round(df.totaldfap2, 2)
        DF3 = round(df.totaldfap3, 2)
    except:
        raise Http404
    return render(request, 'ManagerUI/RiskSummaryMana/RiskMatrixMana.html',
                  {'page': 'riskMatrix', 'API1': location.locat(df.totaldfap1, ca.fcofvalue),
                   'API2': location.locat(df.totaldfap2, ca.fcofvalue),
                   'API3': location.locat(df.totaldfap3, ca.fcofvalue), 'DF1': DF1, 'DF2': DF2, 'DF3': DF3, 'ca': Ca,
                   'siteID': siteID,
                   'ass': rwAss, 'isTank': isTank, 'isShell': isShell, 'df': df, 'proposalID': proposalID,
                   'count': count, 'noti': noti, 'countnoti': countnoti, 'info': request.session})


def Inputdata(request, proposalID):
    try:
        Fluid = ["Acid", "AlCl3", "C1-C2", "C13-C16", "C17-C25", "C25+", "C3-C4", "C5", "C6-C8", "C9-C12", "CO", "DEE",
                 "EE", "EEA", "EG", "EO", "H2", "H2S", "HCl", "HF", "Methanol", "Nitric Acid", "NO2", "Phosgene", "PO",
                 "Pyrophoric", "Steam", "Styrene", "TDI", "Water"]
        rwassessment = models.RwAssessment.objects.get(id=proposalID)
        rwequipment = models.RwEquipment.objects.get(id=proposalID)
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwstream = models.RwStream.objects.get(id=proposalID)
        rwexcor = models.RwExtcorTemperature.objects.get(id=proposalID)
        rwcoat = models.RwCoating.objects.get(id=proposalID)
        rwmaterial = models.RwMaterial.objects.get(id=proposalID)
        rwinputca = models.RwInputCaLevel1.objects.get(id=proposalID)
        assDate = rwassessment.assessmentdate.strftime('%Y-%m-%d')
        try:
            extDate = rwcoat.externalcoatingdate.strftime('%Y-%m-%d')
        except:
            extDate = datetime.now().strftime('%Y-%m-%d')

        comp = models.ComponentMaster.objects.get(componentid=rwassessment.componentid_id)
        data = {}
        if request.method == 'POST':
            data['assessmentname'] = request.POST.get('AssessmentName')
            data['assessmentdate'] = request.POST.get('assessmentdate')
            data['apicomponenttypeid'] = models.ApiComponentType.objects.get(
                apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
            data['equipmentType'] = models.EquipmentType.objects.get(equipmenttypeid=models.EquipmentMaster.objects.get(
                equipmentid=comp.equipmentid_id).equipmenttypeid_id).equipmenttypename
            data['riskperiod'] = request.POST.get('RiskAnalysisPeriod')
            if request.POST.get('adminControlUpset'):
                adminControlUpset = 1
            else:
                adminControlUpset = 0

            if request.POST.get('ContainsDeadlegs'):
                containsDeadlegs = 1
            else:
                containsDeadlegs = 0

            if request.POST.get('Highly'):
                HighlyEffe = 1
            else:
                HighlyEffe = 0

            if request.POST.get('CylicOper'):
                cylicOP = 1
            else:
                cylicOP = 0

            if request.POST.get('Downtime'):
                downtime = 1
            else:
                downtime = 0

            if request.POST.get('SteamedOut'):
                steamOut = 1
            else:
                steamOut = 0

            if request.POST.get('HeatTraced'):
                heatTrace = 1
            else:
                heatTrace = 0

            if request.POST.get('PWHT'):
                pwht = 1
            else:
                pwht = 0

            if request.POST.get('InterfaceSoilWater'):
                interfaceSoilWater = 1
            else:
                interfaceSoilWater = 0

            if request.POST.get('PressurisationControlled'):
                pressureControl = 1
            else:
                pressureControl = 0

            if request.POST.get('LOM'):
                linerOnlineMoniter = 1
            else:
                linerOnlineMoniter = 0

            if request.POST.get('EquOper'):
                lowestTemp = 1
            else:
                lowestTemp = 0

            if request.POST.get('PresenceofSulphidesShutdow'):
                presentSulphidesShutdown = 1
            else:
                presentSulphidesShutdown = 0

            if request.POST.get('MFTF'):
                materialExposed = 1
            else:
                materialExposed = 0

            if request.POST.get('PresenceofSulphides'):
                presentSulphide = 1
            else:
                presentSulphide = 0

            data['minTemp'] = request.POST.get('Min')
            data['ExternalEnvironment'] = request.POST.get('ExternalEnvironment')
            data['ThermalHistory'] = request.POST.get('ThermalHistory')
            data['OnlineMonitoring'] = request.POST.get('OnlineMonitoring')
            data['EquipmentVolumn'] = request.POST.get('EquipmentVolume')

            data['normaldiameter'] = request.POST.get('NominalDiameter')
            data['normalthick'] = request.POST.get('NominalThickness')
            data['currentthick'] = request.POST.get('CurrentThickness')
            data['tmin'] = request.POST.get('tmin')
            data['currentrate'] = request.POST.get('CurrentRate')
            data['deltafatt'] = request.POST.get('DeltaFATT')

            if request.POST.get('DFDI'):
                damageDuringInsp = 1
            else:
                damageDuringInsp = 0

            if request.POST.get('ChemicalInjection'):
                chemicalInj = 1
            else:
                chemicalInj = 0

            if request.POST.get('PresenceCracks'):
                crackpresent = 1
            else:
                crackpresent = 0

            if request.POST.get('HFICI'):
                HFICI = 1
            else:
                HFICI = 0

            if request.POST.get('TrampElements'):
                TrampElement = 1
            else:
                TrampElement = 0

            data['MaxBrinell'] = request.POST.get('MBHW')
            data['complex'] = request.POST.get('ComplexityProtrusions')
            data['CylicLoad'] = request.POST.get('CLC')
            data['branchDiameter'] = request.POST.get('BranchDiameter')
            data['joinTypeBranch'] = request.POST.get('JTB')
            data['numberPipe'] = request.POST.get('NFP')
            data['pipeCondition'] = request.POST.get('PipeCondition')
            data['prevFailure'] = request.POST.get('PreviousFailures')

            if request.POST.get('VASD'):
                visibleSharkingProtect = 1
            else:
                visibleSharkingProtect = 0

            data['shakingPipe'] = request.POST.get('ASP')
            data['timeShakingPipe'] = request.POST.get('ATSP')
            data['correctActionMitigate'] = request.POST.get('CAMV')
            # OP condition
            data['maxOT'] = request.POST.get('MaxOT')
            data['maxOP'] = request.POST.get('MaxOP')
            data['minOT'] = request.POST.get('MinOT')
            data['minOP'] = request.POST.get('MinOP')
            data['OpHydroPressure'] = request.POST.get('OHPP')
            data['criticalTemp'] = request.POST.get('CET')
            data['OP1'] = request.POST.get('Operating1')
            data['OP2'] = request.POST.get('Operating2')
            data['OP3'] = request.POST.get('Operating3')
            data['OP4'] = request.POST.get('Operating4')
            data['OP5'] = request.POST.get('Operating5')
            data['OP6'] = request.POST.get('Operating6')
            data['OP7'] = request.POST.get('Operating7')
            data['OP8'] = request.POST.get('Operating8')
            data['OP9'] = request.POST.get('Operating9')
            data['OP10'] = request.POST.get('Operating10')
            # material
            data['material'] = request.POST.get('Material')
            data['maxDesignTemp'] = request.POST.get('MaxDesignTemp')
            data['minDesignTemp'] = request.POST.get('MinDesignTemp')
            data['designPressure'] = request.POST.get('DesignPressure')
            data['tempRef'] = request.POST.get('ReferenceTemperature')
            data['allowStress'] = request.POST.get('ASAT')
            data['BrittleFacture'] = request.POST.get('BFGT')
            data['CA'] = request.POST.get('CorrosionAllowance')
            data['sigmaPhase'] = request.POST.get('SigmaPhase')
            if request.POST.get('CoLAS'):
                cacbonAlloy = 1
            else:
                cacbonAlloy = 0

            if request.POST.get('AusteniticSteel'):
                austeniticStell = 1
            else:
                austeniticStell = 0

            if request.POST.get('SusceptibleTemper'):
                suscepTemp = 1
            else:
                suscepTemp = 0

            if request.POST.get('NickelAlloy'):
                nickelAlloy = 1
            else:
                nickelAlloy = 0

            if request.POST.get('Chromium'):
                chromium = 1
            else:
                chromium = 0

            data['sulfurContent'] = request.POST.get('SulfurContent')
            data['heatTreatment'] = request.POST.get('heatTreatment')

            if request.POST.get('MGTEHTHA'):
                materialHTHA = 1
            else:
                materialHTHA = 0

            data['HTHAMaterialGrade'] = request.POST.get('HTHAMaterialGrade')

            if request.POST.get('MaterialPTA'):
                materialPTA = 1
            else:
                materialPTA = 0

            data['PTAMaterialGrade'] = request.POST.get('PTAMaterialGrade')
            data['materialCostFactor'] = request.POST.get('MaterialCostFactor')
            # Coating, Clading
            if request.POST.get('InternalCoating'):
                InternalCoating = 1
            else:
                InternalCoating = 0

            if request.POST.get('ExternalCoating'):
                ExternalCoating = 1
            else:
                ExternalCoating = 0

            data['ExternalCoatingID'] = request.POST.get('ExternalCoatingID')
            data['ExternalCoatingQuality'] = request.POST.get('ExternalCoatingQuality')

            if request.POST.get('SCWD'):
                supportMaterial = 1
            else:
                supportMaterial = 0

            if request.POST.get('InternalCladding'):
                InternalCladding = 1
            else:
                InternalCladding = 0

            data['CladdingCorrosionRate'] = request.POST.get('CladdingCorrosionRate')

            if request.POST.get('InternalLining'):
                InternalLining = 1
            else:
                InternalLining = 0

            data['InternalLinerType'] = request.POST.get('InternalLinerType')
            data['InternalLinerCondition'] = request.POST.get('InternalLinerCondition')

            if request.POST.get('ExternalInsulation') == "on" or request.POST.get('ExternalInsulation') == 1:
                ExternalInsulation = 1
            else:
                ExternalInsulation = 0

            if request.POST.get('ICC'):
                InsulationCholride = 1
            else:
                InsulationCholride = 0

            data['ExternalInsulationType'] = request.POST.get('ExternalInsulationType')
            data['InsulationCondition'] = request.POST.get('InsulationCondition')
            # Steam
            data['NaOHConcentration'] = request.POST.get('NaOHConcentration')
            data['ReleasePercentToxic'] = request.POST.get('RFPT')
            data['ChlorideIon'] = request.POST.get('ChlorideIon')
            data['CO3'] = request.POST.get('CO3')
            data['H2SContent'] = request.POST.get('H2SContent')
            data['PHWater'] = request.POST.get('PHWater')

            if request.POST.get('EAGTA'):
                exposureAcid = 1
            else:
                exposureAcid = 0

            if request.POST.get('ToxicConstituents'):
                ToxicConstituents = 1
            else:
                ToxicConstituents = 0

            data['ExposureAmine'] = request.POST.get('ExposureAmine')
            data['AminSolution'] = request.POST.get('ASC')

            if request.POST.get('APDO'):
                aquaDuringOP = 1
            else:
                aquaDuringOP = 0

            if request.POST.get('APDSD'):
                aquaDuringShutdown = 1
            else:
                aquaDuringShutdown = 0

            if request.POST.get('EnvironmentCH2S'):
                EnvironmentCH2S = 1
            else:
                EnvironmentCH2S = 0

            if request.POST.get('PHA'):
                presentHF = 1
            else:
                presentHF = 0

            if request.POST.get('PresenceCyanides'):
                presentCyanide = 1
            else:
                presentCyanide = 0

            if request.POST.get('PCH'):
                processHydrogen = 1
            else:
                processHydrogen = 0

            if request.POST.get('ECCAC'):
                environCaustic = 1
            else:
                environCaustic = 0

            if request.POST.get('ESBC'):
                exposedSulfur = 1
            else:
                exposedSulfur = 0

            if request.POST.get('MEFMSCC'):
                materialExposedFluid = 1
            else:
                materialExposedFluid = 0
            # CA
            data['APIFluid'] = request.POST.get('APIFluid')
            data['MassInventory'] = request.POST.get('MassInventory')
            data['Systerm'] = request.POST.get('Systerm')
            data['MassComponent'] = request.POST.get('MassComponent')
            data['EquipmentCost'] = request.POST.get('EquipmentCost')
            data['MittigationSysterm'] = request.POST.get('MittigationSysterm')
            data['ProductionCost'] = request.POST.get('ProductionCost')
            data['ToxicPercent'] = request.POST.get('ToxicPercent')
            data['InjureCost'] = request.POST.get('InjureCost')
            data['ReleaseDuration'] = request.POST.get('ReleaseDuration')
            data['EnvironmentCost'] = request.POST.get('EnvironmentCost')
            data['PersonDensity'] = request.POST.get('PersonDensity')
            data['DetectionType'] = request.POST.get('DetectionType')
            data['IsulationType'] = request.POST.get('IsulationType')

            rwassessment.assessmentdate = data['assessmentdate']
            rwassessment.proposalname = data['assessmentname']
            rwassessment.save()

            rwequipment.adminupsetmanagement = adminControlUpset
            rwequipment.containsdeadlegs = containsDeadlegs
            rwequipment.cyclicoperation = cylicOP
            rwequipment.highlydeadleginsp = HighlyEffe
            rwequipment.downtimeprotectionused = downtime
            rwequipment.externalenvironment = data['ExternalEnvironment']
            rwequipment.heattraced = heatTrace
            rwequipment.interfacesoilwater = interfaceSoilWater
            rwequipment.lineronlinemonitoring = linerOnlineMoniter
            rwequipment.materialexposedtoclext = materialExposed
            rwequipment.minreqtemperaturepressurisation = data['minTemp']
            rwequipment.onlinemonitoring = data['OnlineMonitoring']
            rwequipment.presencesulphideso2 = presentSulphide
            rwequipment.presencesulphideso2shutdown = presentSulphidesShutdown
            rwequipment.pressurisationcontrolled = pressureControl
            rwequipment.pwht = pwht
            rwequipment.steamoutwaterflush = steamOut
            rwequipment.thermalhistory = data['ThermalHistory']
            rwequipment.yearlowestexptemp = lowestTemp
            rwequipment.volume = data['EquipmentVolumn']
            rwequipment.save()

            rwcomponent.nominaldiameter = data['normaldiameter']
            rwcomponent.nominalthickness = data['normalthick']
            rwcomponent.currentthickness = data['currentthick']
            rwcomponent.minreqthickness = data['tmin']
            rwcomponent.currentcorrosionrate = data['currentrate']
            rwcomponent.branchdiameter = data['branchDiameter']
            rwcomponent.branchjointtype = data['joinTypeBranch']
            rwcomponent.brinnelhardness = data['MaxBrinell']
            rwcomponent.deltafatt = data['deltafatt']
            rwcomponent.chemicalinjection = chemicalInj
            rwcomponent.highlyinjectioninsp = HFICI
            rwcomponent.complexityprotrusion = data['complex']
            rwcomponent.correctiveaction = data['correctActionMitigate']
            rwcomponent.crackspresent = crackpresent
            rwcomponent.cyclicloadingwitin15_25m = data['CylicLoad']
            rwcomponent.damagefoundinspection = damageDuringInsp
            rwcomponent.numberpipefittings = data['numberPipe']
            rwcomponent.pipecondition = data['pipeCondition']
            rwcomponent.previousfailures = data['prevFailure']
            rwcomponent.shakingamount = data['shakingPipe']
            rwcomponent.shakingdetected = visibleSharkingProtect
            rwcomponent.shakingtime = data['timeShakingPipe']
            rwcomponent.allowablestress = data['allowStress']
            # rwcomponent.trampelements=TrampElement
            rwcomponent.save()

            rwstream.aminesolution = data['AminSolution']
            rwstream.aqueousoperation = aquaDuringOP
            rwstream.aqueousshutdown = aquaDuringShutdown
            rwstream.toxicconstituent = ToxicConstituents
            rwstream.caustic = environCaustic
            rwstream.chloride = data['ChlorideIon']
            rwstream.co3concentration = data['CO3']
            rwstream.cyanide = presentCyanide
            rwstream.exposedtogasamine = exposureAcid
            rwstream.exposedtosulphur = exposedSulfur
            rwstream.exposuretoamine = data['ExposureAmine']
            rwstream.h2s = EnvironmentCH2S
            rwstream.h2sinwater = data['H2SContent']
            rwstream.hydrogen = processHydrogen
            rwstream.hydrofluoric = presentHF
            rwstream.materialexposedtoclint = materialExposedFluid
            rwstream.maxoperatingpressure = data['maxOP']
            rwstream.maxoperatingtemperature = float(data['maxOT'])
            rwstream.minoperatingpressure = float(data['minOP'])
            rwstream.minoperatingtemperature = data['minOT']
            rwstream.criticalexposuretemperature = data['criticalTemp']
            rwstream.naohconcentration = data['NaOHConcentration']
            rwstream.releasefluidpercenttoxic = float(data['ReleasePercentToxic'])
            rwstream.waterph = float(data['PHWater'])
            rwstream.h2spartialpressure = float(data['OpHydroPressure'])
            rwstream.save()

            rwexcor.minus12tominus8 = data['OP1']
            rwexcor.minus8toplus6 = data['OP2']
            rwexcor.plus6toplus32 = data['OP3']
            rwexcor.plus32toplus71 = data['OP4']
            rwexcor.plus71toplus107 = data['OP5']
            rwexcor.plus107toplus121 = data['OP6']
            rwexcor.plus121toplus135 = data['OP7']
            rwexcor.plus135toplus162 = data['OP8']
            rwexcor.plus162toplus176 = data['OP9']
            rwexcor.morethanplus176 = data['OP10']
            rwexcor.save()

            rwcoat.externalcoating = ExternalCoating
            rwcoat.externalinsulation = ExternalInsulation
            rwcoat.internalcladding = InternalCladding
            rwcoat.internalcoating = InternalCoating
            rwcoat.internallining = InternalLining
            rwcoat.externalcoatingdate = data['ExternalCoatingID']
            rwcoat.externalcoatingquality = data['ExternalCoatingQuality']
            rwcoat.externalinsulationtype = data['ExternalInsulationType']
            rwcoat.insulationcondition = data['InsulationCondition']
            rwcoat.insulationcontainschloride = InsulationCholride
            rwcoat.internallinercondition = data['InternalLinerCondition']
            rwcoat.internallinertype = data['InternalLinerType']
            rwcoat.claddingcorrosionrate = data['CladdingCorrosionRate']
            rwcoat.supportconfignotallowcoatingmaint = supportMaterial
            rwcoat.save()

            rwmaterial.corrosionallowance = data['CA']
            rwmaterial.materialname = data['material']
            rwmaterial.designpressure = data['designPressure']
            rwmaterial.designtemperature = data['maxDesignTemp']
            rwmaterial.mindesigntemperature = data['minDesignTemp']
            rwmaterial.brittlefracturethickness = data['BrittleFacture']
            rwmaterial.sigmaphase = data['sigmaPhase']
            rwmaterial.sulfurcontent = data['sulfurContent']
            rwmaterial.heattreatment = data['heatTreatment']
            rwmaterial.referencetemperature = data['tempRef']
            rwmaterial.ptamaterialcode = data['PTAMaterialGrade']
            rwmaterial.hthamaterialcode = data['HTHAMaterialGrade']
            rwmaterial.ispta = materialPTA
            rwmaterial.ishtha = materialHTHA
            rwmaterial.austenitic = austeniticStell
            rwmaterial.temper = suscepTemp
            rwmaterial.carbonlowalloy = cacbonAlloy
            rwmaterial.nickelbased = nickelAlloy
            rwmaterial.chromemoreequal12 = chromium
            rwmaterial.costfactor = data['materialCostFactor']
            rwmaterial.save()

            rwinputca.api_fluid = data['APIFluid']
            rwinputca.system = data['Systerm']
            rwinputca.release_duration = data['ReleaseDuration']
            rwinputca.detection_type = data['DetectionType']
            rwinputca.isulation_type = data['IsulationType']
            rwinputca.mitigation_system = data['MittigationSysterm']
            rwinputca.equipment_cost = data['EquipmentCost']
            rwinputca.injure_cost = data['InjureCost']
            rwinputca.evironment_cost = data['EnvironmentCost']
            rwinputca.toxic_percent = data['ToxicPercent']
            rwinputca.personal_density = data['PersonDensity']
            rwinputca.material_cost = data['materialCostFactor']
            rwinputca.production_cost = data['ProductionCost']
            rwinputca.mass_inventory = data['MassInventory']
            rwinputca.mass_component = data['MassComponent']
            rwinputca.stored_pressure = float(data['minOP']) * 6.895
            rwinputca.stored_temp = data['minOT']
            rwinputca.save()

            # Customize code here
            ReCalculate.ReCalculate(proposalID)
            return redirect('inputdata', proposalID=proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'BaseUI/BaseManager/Inputdata.html',
                  {'api': Fluid, 'rwAss': rwassessment, 'rwEq': rwequipment,
                   'rwComp': rwcomponent, 'rwStream': rwstream, 'rwExcot': rwexcor,
                   'rwCoat': rwcoat, 'rwMaterial': rwmaterial, 'rwInputCa': rwinputca,
                   'assDate': assDate, 'extDate': extDate,
                   'componentID': rwassessment.componentid_id,
                   'equipmentID': rwassessment.equipmentid_id})


################ yeu cau kiem dinh Manager ############
def VeriFullyDamageFactorMana(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        print("go VeriFullyDamageFactorMana")
        df = models.RwFullPof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        data = {}
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        siteID = equip.siteid_id
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        data['thinningType'] = df.thinningtype
        data['gfftotal'] = df.gfftotal
        data['fms'] = df.fms
        data['thinningap1'] = roundData.roundDF(df.thinningap1)
        data['thinningap2'] = roundData.roundDF(df.thinningap2)
        data['thinningap3'] = roundData.roundDF(df.thinningap3)
        data['sccap1'] = roundData.roundDF(df.sccap1)
        data['sccap2'] = roundData.roundDF(df.sccap2)
        data['sccap3'] = roundData.roundDF(df.sccap3)
        data['externalap1'] = roundData.roundDF(df.externalap1)
        data['externalap2'] = roundData.roundDF(df.externalap2)
        data['externalap3'] = roundData.roundDF(df.externalap3)
        data['htha_ap1'] = roundData.roundDF(df.htha_ap1)
        data['htha_ap2'] = roundData.roundDF(df.htha_ap2)
        data['htha_ap3'] = roundData.roundDF(df.htha_ap3)
        data['brittleap1'] = roundData.roundDF(df.brittleap1)
        data['brittleap2'] = roundData.roundDF(df.brittleap2)
        data['brittleap3'] = roundData.roundDF(df.brittleap3)
        data['fatigueap1'] = roundData.roundDF(df.fatigueap1)
        data['fatigueap2'] = roundData.roundDF(df.fatigueap2)
        data['fatigueap3'] = roundData.roundDF(df.fatigueap3)
        data['thinninggeneralap1'] = roundData.roundDF(df.thinninggeneralap1)
        data['thinninggeneralap2'] = roundData.roundDF(df.thinninggeneralap2)
        data['thinninggeneralap3'] = roundData.roundDF(df.thinninggeneralap3)
        data['thinninglocalap1'] = roundData.roundDF(df.thinninglocalap1)
        data['thinninglocalap2'] = roundData.roundDF(df.thinninglocalap2)
        data['thinninglocalap3'] = roundData.roundDF(df.thinninglocalap3)
        data['totaldfap1'] = roundData.roundDF(df.totaldfap1)
        data['totaldfap2'] = roundData.roundDF(df.totaldfap2)
        data['totaldfap3'] = roundData.roundDF(df.totaldfap3)
        data['pofap1'] = roundData.roundPoF(df.pofap1)
        data['pofap2'] = roundData.roundPoF(df.pofap2)
        data['pofap3'] = roundData.roundPoF(df.pofap3)
        data['pofap1category'] = df.pofap1category
        data['pofap2category'] = df.pofap2category
        data['pofap3category'] = df.pofap3category
        print("test data")
        # if request.method == 'POST':
        #     df.thinningtype = request.POST.get('thinningType')
        #     df.save()
        #     ReCalculate.ReCalculate(proposalID)
        #     return redirect('veridamgeFactorMana', proposalID)
        if 'Verifica' in request.POST:
            print("go verifiaca")
            veri = models.Verification(proposal=rwAss.proposalname, Is_active=0, manager=request.session['name'],
                                       facility=equip.facilityid_id, com=component.componentname,
                                       eq=equip.equipmentname)
            veri.save()
            some_var = request.POST.getlist('check')
            for some_var in some_var:
                vericontent = models.VeriContent(Verification_id=veri.id, content=some_var)
                vericontent.save()
            return HttpResponse("Bạn đã yêu cầu kiểm định thành công")

    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'ManagerUI/verification_requirments/FullDFV.html',
                  {'page': 'damageFactor', 'obj': data, 'assess': rwAss, 'isTank': isTank, 'siteID':siteID,
                   'isShell': isShell, 'proposalID': proposalID, 'count': count, 'noti': noti, 'countnoti': countnoti,
                   'info': request.session})


def VeriFullyConsequenceMana(request, proposalID):
    data = {}
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        print(" vào VeriFullyConsequenceMana")
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        siteID = equip.siteid_id
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        if isBottom:
            bottomConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['hydraulic_water'] = roundData.roundFC(bottomConsequences.hydraulic_water)
            data['hydraulic_fluid'] = roundData.roundFC(bottomConsequences.hydraulic_fluid)
            data['seepage_velocity'] = roundData.roundFC(bottomConsequences.seepage_velocity)
            data['flow_rate_d1'] = roundData.roundFC(bottomConsequences.flow_rate_d1)
            data['flow_rate_d4'] = roundData.roundFC(bottomConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(bottomConsequences.leak_duration_d1)
            data['leak_duration_d4'] = roundData.roundFC(bottomConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(bottomConsequences.release_volume_leak_d1)
            data['release_volume_leak_d4'] = roundData.roundFC(bottomConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(bottomConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(bottomConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(bottomConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(bottomConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(bottomConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(bottomConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(bottomConsequences.fc_environ)
            data['material_factor'] = bottomConsequences.material_factor
            data['component_damage_cost'] = roundData.roundMoney(bottomConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(bottomConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(bottomConsequences.consequence)
            data['consequencecategory'] = bottomConsequences.consequencecategory
            if 'Verifica' in request.POST:
                veri = models.Verification(proposal=rwAss.proposalname, Is_active=0, manager=request.session['name'],
                                           facility=equip.facilityid_id, com=component.componentname,
                                           eq=equip.equipmentname)
                veri.save()
                some_var = request.POST.getlist('check')
                for some_var in some_var:
                    print(some_var)
                    vericontent = models.VeriContent(Verification_id=veri.id, content=some_var)
                    vericontent.save()
                return HttpResponse("Bạn đã yêu cầu kiểm định thành công")
            return render(request, 'ManagerUI/verification_requirments/fullyBottomConsequenVerification.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID,'siteID':siteID, 'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session})
        elif isShell:
            shellConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['flow_rate_d1'] = roundData.roundFC(shellConsequences.flow_rate_d1)
            data['flow_rate_d2'] = roundData.roundFC(shellConsequences.flow_rate_d2)
            data['flow_rate_d3'] = roundData.roundFC(shellConsequences.flow_rate_d3)
            data['flow_rate_d4'] = roundData.roundFC(shellConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(shellConsequences.leak_duration_d1)
            data['leak_duration_d2'] = roundData.roundFC(shellConsequences.leak_duration_d2)
            data['leak_duration_d3'] = roundData.roundFC(shellConsequences.leak_duration_d3)
            data['leak_duration_d4'] = roundData.roundFC(shellConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(shellConsequences.release_volume_leak_d1)
            data['release_volume_leak_d2'] = roundData.roundFC(shellConsequences.release_volume_leak_d2)
            data['release_volume_leak_d3'] = roundData.roundFC(shellConsequences.release_volume_leak_d3)
            data['release_volume_leak_d4'] = roundData.roundFC(shellConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(shellConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(shellConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(shellConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(shellConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(shellConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(shellConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(shellConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(shellConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(shellConsequences.fc_environ)
            data['component_damage_cost'] = roundData.roundMoney(shellConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(shellConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(shellConsequences.consequence)
            data['consequencecategory'] = shellConsequences.consequencecategory
            if 'Verifica' in request.POST:
                veri = models.Verification(proposal=rwAss.proposalname, Is_active=0, manager=request.session['name'],
                                           facility=equip.facilityid_id, com=component.componentname,
                                           eq=equip.equipmentname)
                veri.save()
                some_var = request.POST.getlist('check')
                for some_var in some_var:
                    print(some_var)
                    vericontent = models.VeriContent(Verification_id=veri.id, content=some_var)
                    vericontent.save()
                return HttpResponse("Bạn đã yêu cầu kiểm định thành công")
            return render(request, 'ManagerUI/verification_requirments/fullyShellConsequenceVerification.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID,'siteID':siteID,'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session})
        else:
            print("vào lại loại thường")
            ca = models.RwCaLevel1.objects.get(id=proposalID)
            inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
            data['production_cost'] = roundData.roundMoney(inputCa.production_cost)
            data['equipment_cost'] = roundData.roundMoney(inputCa.equipment_cost)
            data['personal_density'] = inputCa.personal_density
            data['evironment_cost'] = roundData.roundMoney(inputCa.evironment_cost)
            data['ca_cmd'] = roundData.roundFC(ca.ca_cmd)
            data['ca_inj_flame'] = roundData.roundFC(ca.ca_inj_flame)
            data['fc_cmd'] = roundData.roundMoney(ca.fc_cmd)
            data['fc_affa'] = roundData.roundMoney(ca.fc_affa)
            data['fc_prod'] = roundData.roundMoney(ca.fc_prod)
            data['fc_inj'] = roundData.roundMoney(ca.fc_inj)
            data['fc_envi'] = roundData.roundMoney(ca.fc_envi)
            data['fc_total'] = roundData.roundMoney(ca.fc_total)
            data['fcof_category'] = ca.fcof_category
            print("đưa dữ liệu vào mảng")
            if 'Verifica' in request.POST:
                veri = models.Verification(proposal=rwAss.proposalname, Is_active=0, manager=request.session['name'],
                                           facility=equip.facilityid_id, com=component.componentname,
                                           eq=equip.equipmentname)
                veri.save()
                some_var = request.POST.getlist('check')
                for some_var in some_var:
                    print(some_var)
                    vericontent = models.VeriContent(Verification_id=veri.id, content=some_var)
                    vericontent.save()
                return HttpResponse("Bạn đã yêu cầu kiểm định thành công")
            return render(request, 'ManagerUI/verification_requirments/fullyNormalConsequenceVericification.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'siteID':siteID,'ass': rwAss, 'count': count,
                           'noti': noti, 'countnoti': countnoti, 'info': request.session})
    except Exception as e:
        print(e)
        raise Http404


def VerificationHome(request, faciid):
    try:
        faci = models.Facility.objects.filter(facilityid=faciid)
        array = []
        for a in faci:
            print("go veri")
            veri = models.Verification.objects.filter(facility=a.facilityid)
            ct = models.VeriContent.objects.all()
            for verifi in veri:
                print(verifi.id)
                cont = models.VeriContent.objects.filter(Verification=verifi.id)
                array.append(cont)
                for con in cont:
                    print(con.Verification.id)
        if '_check' in request.POST:
            veriCheck_ID = request.POST.get('_check')
            return redirect('VerificationCheck', verifiID=veriCheck_ID)
        return render(request, 'ManagerUI/verification_requirments/VerificationContent.html',
                      {'veri': veri, 'faci': faci, 'cont': cont, 'ct': ct, 'arr': array})
    except Exception as e:
        print(e)
        return render(request, 'ManagerUI/verification_requirments/VerificationHome.html')


def VerificationNumberFacilities(request):
    siteid = models.Sites.objects.filter(userID_id=request.session['id'])[0].siteid
    faci = models.Facility.objects.filter(siteid=siteid)
    array = []
    return render(request, 'ManagerUI/verification_requirments/VerificationNumberFacilities.html', {'faci': faci})


def VerificationCheck(request, verifiID):
    veri = models.Verification.objects.get(id=verifiID)
    veri.Is_active = 1
    veri.save()
    return HttpResponse("Da Xem")


################ Citizen UI control ###################
def citizen_home(request):
    try:
        risk = []
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        com = models.Zbusiness.objects.all()
        for c in com:
            dataF = {}
            dataF['id'] = c.id
            dataF['namecompany'] = c.namecompany
            dataF['compainfor'] = c.compainfor
            us = models.ZUser.objects.get(id=c.userID_id)
            dataF['phone'] = us.phone
            dataF['email'] = us.email
            dataF['name'] = us.name
            dataF['add'] = us.adress
            si = models.Sites.objects.get(sitename=dataF['namecompany'])
            dataF['siteID'] = si.siteid
            risk.append(dataF)
    except Exception as e:
        print(e)
    return render(request, 'CitizenUI/CitizenHome.html',
                  {'info': request.session, 'count': count, 'risk': risk, 'noti': noti, 'countnoti': countnoti})


def ListfacilityCitizen(request, siteID):
    try:
        risk = []
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        site = models.Sites.objects.get(siteid=siteID)
        faci = models.Facility.objects.filter(siteid=siteID)
        si = models.Zbusiness.objects.get(namecompany=site.sitename)
        name = models.ZUser.objects.get(id=site.userID_id)
    except Exception as e:
        print(e)
    return render(request, 'CitizenUI/infor_facility.html',
                  {'page': 'inforCompany', 'info': request.session, 'site': site, 'faci': faci, 'si': si,
                   'count': count, 'name': name, 'noti': noti, 'countnoti': countnoti})


def ListProposalCitizen(request, facilityID, siteID):
    try:
        data = []
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        site = models.Sites.objects.get(siteid=siteID)
        faci = models.Facility.objects.filter(siteid=siteID)
        eq = models.EquipmentMaster.objects.filter(facilityid=facilityID)
        for eq in eq:
            com = models.ComponentMaster.objects.filter(equipmentid=eq.equipmentid)
            for com in com:
                # print(com.componentid)

                rwass = models.RwAssessment.objects.filter(componentid=com.componentid)
                comp = models.ComponentMaster.objects.get(componentid=com.componentid)
                equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
                tank = [8, 12, 14, 15]
                for a in rwass:
                    df = models.RwFullPof.objects.filter(id=a.id)
                    fc = models.RwFullFcof.objects.filter(id=a.id)
                    dm = models.RwDamageMechanism.objects.filter(id_dm=a.id)
                    obj1 = {}
                    obj1['id'] = a.id
                    obj1['name'] = a.proposalname
                    obj1['lastinsp'] = a.assessmentdate.strftime('%Y-%m-%d')
                    if df.count() != 0:
                        obj1['df'] = round(df[0].totaldfap1, 2)
                        obj1['gff'] = df[0].gfftotal
                        obj1['fms'] = df[0].fms
                    else:
                        obj1['df'] = 0
                        obj1['gff'] = 0
                        obj1['fms'] = 0
                    if fc.count() != 0:
                        obj1['fc'] = round(fc[0].fcofvalue, 2)
                    else:
                        obj1['fc'] = 0
                    if dm.count() != 0:
                        obj1['duedate'] = dm[0].inspduedate.date().strftime('%Y-%m-%d')
                    else:
                        obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=15)).strftime('%Y-%m-%d')
                        obj1['lastinsp'] = equip.commissiondate.date().strftime('%Y-%m-%d')
                    obj1['risk'] = round(obj1['df'] * obj1['gff'] * obj1['fms'] * obj1['fc'], 2)
                    data.append(obj1)
                pagidata = Paginator(data, 25)
                pagedata = request.GET.get('page', 1)
                try:
                    obj = pagidata.page(pagedata)
                except PageNotAnInteger:
                    obj = pagidata.page(1)
                except EmptyPage:
                    obj = pagedata.page(pagidata.num_pages)

                if comp.componenttypeid_id in tank:
                    istank = 1
                else:
                    istank = 0
                if comp.componenttypeid_id == 8 or comp.componenttypeid_id == 14:
                    isshell = 1
                else:
                    isshell = 0
    except Exception as e:
        print(e)
    return render(request, 'CitizenUI/ListProposalCitizen.html',
                  {'page': 'listProposal', 'info': request.session, 'site': site, 'faci': faci, 'obj': obj,
                   'noti': noti, 'countnoti': countnoti, 'count': count})


def RiskMatrixCitizen(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        locatAPI1 = {}
        locatAPI2 = {}
        locatAPI3 = {}
        locatAPI1['x'] = 0
        locatAPI1['y'] = 500

        locatAPI2['x'] = 0
        locatAPI2['y'] = 500

        locatAPI3['x'] = 0
        locatAPI3['y'] = 500

        df = models.RwFullPof.objects.get(id=proposalID)
        ca = models.RwFullFcof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0

        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        Ca = round(ca.fcofvalue, 2)
        DF1 = round(df.totaldfap1, 2)
        DF2 = round(df.totaldfap2, 2)
        DF3 = round(df.totaldfap3, 2)
    except:
        raise Http404
    return render(request, 'CitizenUI/risk_summary_Citizen/riskMatrix_Citizen.html',
                  {'page': 'riskMatrix', 'API1': location.locat(df.totaldfap1, ca.fcofvalue),
                   'API2': location.locat(df.totaldfap2, ca.fcofvalue),
                   'API3': location.locat(df.totaldfap3, ca.fcofvalue), 'DF1': DF1, 'DF2': DF2, 'DF3': DF3, 'ca': Ca,
                   'ass': rwAss, 'isTank': isTank, 'isShell': isShell, 'df': df, 'proposalID': proposalID,
                   'info': request.session,
                   'component': component, 'equip': equip, 'faci': faci, 'si': si, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def FullyDamageFactorCitizen(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        df = models.RwFullPof.objects.get(id=proposalID)
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        data = {}
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        data['thinningType'] = df.thinningtype
        data['gfftotal'] = df.gfftotal
        data['fms'] = df.fms
        data['thinningap1'] = roundData.roundDF(df.thinningap1)
        data['thinningap2'] = roundData.roundDF(df.thinningap2)
        data['thinningap3'] = roundData.roundDF(df.thinningap3)
        data['sccap1'] = roundData.roundDF(df.sccap1)
        data['sccap2'] = roundData.roundDF(df.sccap2)
        data['sccap3'] = roundData.roundDF(df.sccap3)
        data['externalap1'] = roundData.roundDF(df.externalap1)
        data['externalap2'] = roundData.roundDF(df.externalap2)
        data['externalap3'] = roundData.roundDF(df.externalap3)
        data['htha_ap1'] = roundData.roundDF(df.htha_ap1)
        data['htha_ap2'] = roundData.roundDF(df.htha_ap2)
        data['htha_ap3'] = roundData.roundDF(df.htha_ap3)
        data['brittleap1'] = roundData.roundDF(df.brittleap1)
        data['brittleap2'] = roundData.roundDF(df.brittleap2)
        data['brittleap3'] = roundData.roundDF(df.brittleap3)
        data['fatigueap1'] = roundData.roundDF(df.fatigueap1)
        data['fatigueap2'] = roundData.roundDF(df.fatigueap2)
        data['fatigueap3'] = roundData.roundDF(df.fatigueap3)
        data['thinninggeneralap1'] = roundData.roundDF(df.thinninggeneralap1)
        data['thinninggeneralap2'] = roundData.roundDF(df.thinninggeneralap2)
        data['thinninggeneralap3'] = roundData.roundDF(df.thinninggeneralap3)
        data['thinninglocalap1'] = roundData.roundDF(df.thinninglocalap1)
        data['thinninglocalap2'] = roundData.roundDF(df.thinninglocalap2)
        data['thinninglocalap3'] = roundData.roundDF(df.thinninglocalap3)
        data['totaldfap1'] = roundData.roundDF(df.totaldfap1)
        data['totaldfap2'] = roundData.roundDF(df.totaldfap2)
        data['totaldfap3'] = roundData.roundDF(df.totaldfap3)
        data['pofap1'] = roundData.roundPoF(df.pofap1)
        data['pofap2'] = roundData.roundPoF(df.pofap2)
        data['pofap3'] = roundData.roundPoF(df.pofap3)
        data['pofap1category'] = df.pofap1category
        data['pofap2category'] = df.pofap2category
        data['pofap3category'] = df.pofap3category
        if request.method == 'POST':
            df.thinningtype = request.POST.get('thinningType')
            df.save()
            ReCalculate.ReCalculate(proposalID)
            return redirect('damgeFactor', proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'CitizenUI/risk_summary_Citizen/dfFull_Citizen.html',
                  {'page': 'damageFactor', 'obj': data, 'assess': rwAss, 'isTank': isTank,
                   'isShell': isShell, 'proposalID': proposalID, 'info': request.session,
                   'component': component, 'equip': equip, 'faci': faci, 'si': si, 'noti': noti, 'countnoti': countnoti,
                   'count': count})


def FullyConsequenceCitizen(request, proposalID):
    data = {}
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwAss = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        if component.componenttypeid_id == 12 or component.componenttypeid_id == 15:
            isBottom = 1
        else:
            isBottom = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        if isBottom:
            bottomConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['hydraulic_water'] = roundData.roundFC(bottomConsequences.hydraulic_water)
            data['hydraulic_fluid'] = roundData.roundFC(bottomConsequences.hydraulic_fluid)
            data['seepage_velocity'] = roundData.roundFC(bottomConsequences.seepage_velocity)
            data['flow_rate_d1'] = roundData.roundFC(bottomConsequences.flow_rate_d1)
            data['flow_rate_d4'] = roundData.roundFC(bottomConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(bottomConsequences.leak_duration_d1)
            data['leak_duration_d4'] = roundData.roundFC(bottomConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(bottomConsequences.release_volume_leak_d1)
            data['release_volume_leak_d4'] = roundData.roundFC(bottomConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(bottomConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(bottomConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(bottomConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(bottomConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(bottomConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(bottomConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(bottomConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(bottomConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(bottomConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(bottomConsequences.fc_environ)
            data['material_factor'] = bottomConsequences.material_factor
            data['component_damage_cost'] = roundData.roundMoney(bottomConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(bottomConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(bottomConsequences.consequence)
            data['consequencecategory'] = bottomConsequences.consequencecategory
            return render(request, 'CitizenUI/risk_summary_Citizen/fullyBottomConsequence_Citizen.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session, 'component': component,
                           'equip': equip, 'faci': faci, 'si': si, 'noti': noti, 'countnoti': countnoti,
                           'count': count})
        elif isShell:
            shellConsequences = models.RwCaTank.objects.get(id=proposalID)
            data['flow_rate_d1'] = roundData.roundFC(shellConsequences.flow_rate_d1)
            data['flow_rate_d2'] = roundData.roundFC(shellConsequences.flow_rate_d2)
            data['flow_rate_d3'] = roundData.roundFC(shellConsequences.flow_rate_d3)
            data['flow_rate_d4'] = roundData.roundFC(shellConsequences.flow_rate_d4)
            data['leak_duration_d1'] = roundData.roundFC(shellConsequences.leak_duration_d1)
            data['leak_duration_d2'] = roundData.roundFC(shellConsequences.leak_duration_d2)
            data['leak_duration_d3'] = roundData.roundFC(shellConsequences.leak_duration_d3)
            data['leak_duration_d4'] = roundData.roundFC(shellConsequences.leak_duration_d4)
            data['release_volume_leak_d1'] = roundData.roundFC(shellConsequences.release_volume_leak_d1)
            data['release_volume_leak_d2'] = roundData.roundFC(shellConsequences.release_volume_leak_d2)
            data['release_volume_leak_d3'] = roundData.roundFC(shellConsequences.release_volume_leak_d3)
            data['release_volume_leak_d4'] = roundData.roundFC(shellConsequences.release_volume_leak_d4)
            data['release_volume_rupture'] = roundData.roundFC(shellConsequences.release_volume_rupture)
            data['time_leak_ground'] = roundData.roundFC(shellConsequences.time_leak_ground)
            data['volume_subsoil_leak_d1'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d1)
            data['volume_subsoil_leak_d4'] = roundData.roundFC(shellConsequences.volume_subsoil_leak_d4)
            data['volume_ground_water_leak_d1'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d1)
            data['volume_ground_water_leak_d4'] = roundData.roundFC(shellConsequences.volume_ground_water_leak_d4)
            data['barrel_dike_rupture'] = roundData.roundFC(shellConsequences.barrel_dike_rupture)
            data['barrel_onsite_rupture'] = roundData.roundFC(shellConsequences.barrel_onsite_rupture)
            data['barrel_offsite_rupture'] = roundData.roundFC(shellConsequences.barrel_offsite_rupture)
            data['barrel_water_rupture'] = roundData.roundFC(shellConsequences.barrel_water_rupture)
            data['fc_environ_leak'] = roundData.roundMoney(shellConsequences.fc_environ_leak)
            data['fc_environ_rupture'] = roundData.roundMoney(shellConsequences.fc_environ_rupture)
            data['fc_environ'] = roundData.roundMoney(shellConsequences.fc_environ)
            data['component_damage_cost'] = roundData.roundMoney(shellConsequences.component_damage_cost)
            data['business_cost'] = roundData.roundMoney(shellConsequences.business_cost)
            data['consequence'] = roundData.roundMoney(shellConsequences.consequence)
            data['consequencecategory'] = shellConsequences.consequencecategory
            return render(request, 'CitizenUI/risk_summary_Citizen/fullyShellConsequence_Citizen.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session,
                           'component': component, 'equip': equip, 'faci': faci, 'si': si, 'noti': noti,
                           'countnoti': countnoti, 'count': count})
        else:
            ca = models.RwCaLevel1.objects.get(id=proposalID)
            inputCa = models.RwInputCaLevel1.objects.get(id=proposalID)
            data['production_cost'] = roundData.roundMoney(inputCa.production_cost)
            data['equipment_cost'] = roundData.roundMoney(inputCa.equipment_cost)
            data['personal_density'] = inputCa.personal_density
            data['evironment_cost'] = roundData.roundMoney(inputCa.evironment_cost)
            data['ca_cmd'] = roundData.roundFC(ca.ca_cmd)
            data['ca_inj_flame'] = roundData.roundFC(ca.ca_inj_flame)
            data['fc_cmd'] = roundData.roundMoney(ca.fc_cmd)
            data['fc_affa'] = roundData.roundMoney(ca.fc_affa)
            data['fc_prod'] = roundData.roundMoney(ca.fc_prod)
            data['fc_inj'] = roundData.roundMoney(ca.fc_inj)
            data['fc_envi'] = roundData.roundMoney(ca.fc_envi)
            data['fc_total'] = roundData.roundMoney(ca.fc_total)
            data['fcof_category'] = ca.fcof_category
            return render(request, 'CitizenUI/risk_summary_Citizen/fullyNormalConsequence_Citizen.html',
                          {'page': 'fullyConse', 'data': data, 'proposalID': proposalID, 'ass': rwAss,
                           'info': request.session,
                           'component': component, 'equip': equip, 'faci': faci, 'si': si, 'noti': noti,
                           'countnoti': countnoti, 'count': count})
    except:
        raise Http404


def RiskChartCitizen(request, proposalID):
    try:
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        rwAssessment = models.RwAssessment.objects.get(id=proposalID)
        component = models.ComponentMaster.objects.get(componentid=rwAssessment.componentid_id)
        equip = models.EquipmentMaster.objects.get(equipmentid=component.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        rwFullpof = models.RwFullPof.objects.get(id=proposalID)
        rwFullcof = models.RwFullFcof.objects.get(id=proposalID)
        risk = rwFullpof.pofap1 * rwFullcof.fcofvalue
        chart = models.RwDataChart.objects.get(id=proposalID)
        assessmentDate = rwAssessment.assessmentdate
        dataChart = [risk, chart.riskage1, chart.riskage2, chart.riskage3, chart.riskage4, chart.riskage5,
                     chart.riskage6,
                     chart.riskage7, chart.riskage8, chart.riskage9, chart.riskage9, chart.riskage10, chart.riskage11,
                     chart.riskage12, chart.riskage13, chart.riskage14, chart.riskage15]
        dataLabel = [date2Str.date2str(assessmentDate), date2Str.date2str(date2Str.dateFuture(assessmentDate, 1)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 2)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 3)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 4)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 5)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 6)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 7)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 8)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 9)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 10)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 11)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 12)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 13)),
                     date2Str.date2str(date2Str.dateFuture(assessmentDate, 14))]
        dataTarget = [chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget,
                      chart.risktarget,
                      chart.risktarget, chart.risktarget, chart.risktarget, chart.risktarget]
        endLabel = date2Str.date2str(date2Str.dateFuture(assessmentDate, 15))
        content = {'page': 'riskChart', 'label': dataLabel, 'data': dataChart, 'target': dataTarget,
                   'endLabel': endLabel, 'proposalname': rwAssessment.proposalname,
                   'proposalID': rwAssessment.id, 'componentID': rwAssessment.componentid_id, 'info': request.session,
                   'component': component, 'equip': equip, 'faci': faci, 'si': si, 'noti': noti, 'countnoti': countnoti,
                   'count': count}
        return render(request, 'CitizenUI/risk_summary_Citizen/riskChart_Citizen.html', content)
    except:
        raise Http404


###########connect thingsboard _____ sensor, gateway #############
def NewSensor(request, componentID):
    try:
        noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
        countnoti = noti.filter(state=0).count()
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        site = models.Sites.objects.get(siteid=faci.siteid_id)
        sensordata = models.ZSensor.objects.filter(Componentid=componentID)
        data = {}
        if (sensordata.count() == 0):
            if request.method == 'POST':
                print(site.siteid)
                gateway = models.ZGateWay.objects.filter(siteid=site.siteid)[0].idgateway
                print(gateway)
                print("2")
                data['sensorName'] = request.POST.get('sensorName')
                data['accessToken'] = request.POST.get('accessToken')
                a = models.ZSensor(Name=data['sensorName'], Token=data['accessToken'], Gatewayid_id=gateway,
                                   Equipmentid_id=equip.equipmentid, Componentid_id=comp.componentid,
                                   Facilityid_id=faci.facilityid)
                a.save()
            return render(request, 'FacilityUI/proposal/NewSensor.html',
                          {'comp': comp, 'equip': equip, 'faci': faci, 'page': 'newsensor', 'componentID': componentID,
                           'equipmentID': comp.equipmentid_id, 'info': request.session, 'noti': noti,
                           'countnoti': countnoti, 'count': count})
        else:
            packagedata = models.PackageSensor.objects.filter(idsensor=sensordata[0].idsensor)
            if '_delete' in request.POST:
                for pac in packagedata:
                    if request.POST.get('%d' % pac.idpackage):
                        pac.delete()
                return redirect('newsensor', componentID=componentID)
            if '_new' in request.POST:
                print("okok")
                try:
                    print("1")
                    thingsboard = subscribe_thingsboard.Subscribe_thingsboard(componentID)
                    thingsboard.SUBTHINGSBOARD()
                except:
                    print("connect error")
                return redirect('newsensor', componentID=componentID)
            if '_edit' in request.POST:
                return redirect('sensorchart', componentID)
            return render(request, 'FacilityUI/proposal/SensorConnect.html',
                          {'sensorName': sensordata[0].Name, 'comp': comp, 'equip': equip, 'faci': faci,
                           'page': 'newsensor', 'componentID': componentID,
                           'equipmentID': comp.equipmentid_id, 'info': request.session, 'noti': noti,
                           'countnoti': countnoti, 'count': count, 'packagedata': packagedata})
    except Exception as e:
        print(e)
        raise Http404


import json


def DataChart(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    # comp = models.ComponentMaster.objects.get(componentid=componentID)
    # equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
    # faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
    # site = models.Sites.objects.get(siteid=faci.siteid_id)
    sensordata = models.ZSensor.objects.filter(Componentid=componentID)
    packagedata = models.PackageSensor.objects.filter(idsensor=sensordata[0].idsensor)
    humidity = []
    temperature = []
    luminance = []
    datetimes = []
    for da in packagedata:
        data = json.loads(da.package)
        humidity.append(data['humidity'])
        temperature.append(data['temperature'])
        luminance.append(data['luminance'])
        datetimes.append(da.created)
    return render(request, 'FacilityUI/proposal/SensorChart.html',
                  {'sensorName': sensordata[0].Name, 'page': 'newsensor', 'componentID': componentID,
                   'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count, 'humidity': humidity, 'temperature': temperature,
                   'luminance': luminance, 'datetimes': datetimes})


# Đạt 18/08/2020
def ReportProposal(request, componentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        rwass = models.RwAssessment.objects.filter(componentid=componentID)
        data = []
        comp = models.ComponentMaster.objects.get(componentid=componentID)
        equip = models.EquipmentMaster.objects.get(equipmentid=comp.equipmentid_id)
        faci = models.Facility.objects.get(facilityid=equip.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        tank = [8, 12, 14, 15]
        for a in rwass:
            df = models.RwFullPof.objects.filter(id=a.id)
            fc = models.RwFullFcof.objects.filter(id=a.id)
            dm = models.RwDamageMechanism.objects.filter(id_dm=a.id)
            obj1 = {}
            obj1['id'] = a.id
            obj1['name'] = a.proposalname
            obj1['lastinsp'] = a.assessmentdate.strftime('%Y-%m-%d')
            if df.count() != 0:
                obj1['df'] = round(df[0].totaldfap1, 2)
                obj1['gff'] = df[0].gfftotal
                obj1['fms'] = df[0].fms
            else:
                obj1['df'] = 0
                obj1['gff'] = 0
                obj1['fms'] = 0
            if fc.count() != 0:
                obj1['fc'] = round(fc[0].fcofvalue, 2)
            else:
                obj1['fc'] = 0
            if dm.count() != 0:
                obj1['duedate'] = dm[0].inspduedate.date().strftime('%Y-%m-%d')
            else:
                obj1['duedate'] = (a.assessmentdate.date() + relativedelta(years=15)).strftime('%Y-%m-%d')
                obj1['lastinsp'] = equip.commissiondate.date().strftime('%Y-%m-%d')
            obj1['risk'] = round(obj1['df'] * obj1['gff'] * obj1['fms'] * obj1['fc'], 2)
            data.append(obj1)
        pagidata = Paginator(data, 25)
        pagedata = request.GET.get('page', 1)
        try:
            obj = pagidata.page(pagedata)
        except PageNotAnInteger:
            obj = pagidata.page(1)
        except EmptyPage:
            obj = pagedata.page(pagidata.num_pages)

        if comp.componenttypeid_id in tank:
            istank = 1
        else:
            istank = 0
        if comp.componenttypeid_id == 8 or comp.componenttypeid_id == 14:
            isshell = 1
        else:
            isshell = 0
    except:
        raise Http404
    return render(request, 'ManagerUI/Report_Proposal.html',
                  {'page': 'reportproposal', 'obj': obj, 'istank': istank, 'isshell': isshell,
                   'componentID': componentID,
                   'equipmentID': comp.equipmentid_id, 'comp': comp, 'equip': equip, 'faci': faci, 'si': si,
                   'count': count, 'noti': noti, 'countnoti': countnoti, 'info': request.session})


def base_report(request, siteID):
    try:
        count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                              Q(Is_see=0)).count()
    except:
        Http404
    return render(request, 'BaseUI/BaseWeb/basedat.html', {'siteID': siteID, 'count': count})


# def mitigation(request):
#     noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
#     countnoti = noti.filter(state=0).count()
#     count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
#                                           Q(Is_see=0)).count()
#     return render(request, 'FacilityUI/risk_summary/mitigation.html', {'page': 'mitigation'})

def ReportMana(request):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    # print(siteID)
    try:
        risk = []
        data = models.Sites.objects.all()
        for a in data:
            dataF = {}
            dataF['ID'] = a.siteid
            dataF['CreatedTime'] = a.create
            dataF['SiteName'] = a.sitename
            risk.append(dataF)
        pagiFaci = Paginator(risk, 25)
        pageFaci = request.GET.get('page', 1)
        try:
            users = pagiFaci.page(pageFaci)
        except PageNotAnInteger:
            users = pagiFaci.page(1)
        except EmptyPage:
            users = pageFaci.page(pagiFaci.num_pages)
        list = []
        print("hjxhjx")
        if '_viewdetail' in request.POST:
            print("ccacscsa")
            for a in data:
                if (request.POST.get('%d' % a.siteid)):
                    dataA = {}
                    dataA['ID'] = a.siteid
                    dataA['Name'] = a.sitename
                    list.append(dataA)
                    print(list)
            return redirect('facilitiesEdit', a.siteid)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'ManagerUI/Report_Mana.html',
                  {'page': 'reportmana', 'obj': users, 'list': list, 'data': dataF, 'count': count, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})


def ReportFacilities(request, siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        risk = []
        si = models.Sites.objects.get(siteid=siteID)
        data = models.Facility.objects.filter(siteid=siteID)
        for a in data:
            dataF = {}
            risTarget = models.FacilityRiskTarget.objects.get(facilityid=a.facilityid)
            dataF['ID'] = a.facilityid
            dataF['CreatedTime'] = a.create
            dataF['FacilitiName'] = a.facilityname
            dataF['ManagementFactor'] = a.managementfactor
            dataF['RiskTarget'] = risTarget.risktarget_fc
            risk.append(dataF)

        pagiFaci = Paginator(risk, 25)
        pageFaci = request.GET.get('page', 1)
        try:
            users = pagiFaci.page(pageFaci)
        except PageNotAnInteger:
            users = pagiFaci.page(1)
        except EmptyPage:
            users = pageFaci.page(pagiFaci.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/Report_Facilities.html',
                  {'page': 'reportfacilities', 'obj': users, 'siteID': siteID, 'count': count, 'si': si, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})


def ReportEquipment(request, facilityID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        faci = models.Facility.objects.get(facilityid=facilityID)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        data = models.EquipmentMaster.objects.filter(facilityid=facilityID)
        pagiEquip = Paginator(data, 25)
        pageEquip = request.GET.get('page', 1)
        try:
            obj = pagiEquip.page(pageEquip)
        except PageNotAnInteger:
            obj = pagiEquip.page(1)
        except EmptyPage:
            obj = pageEquip.page(pagiEquip.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/Report_Equipment.html',
                  {'page': 'reportequipment', 'obj': obj, 'facilityID': facilityID, 'faci': faci, 'si': si,
                   'count': count, 'noti': noti, 'countnoti': countnoti, 'info': request.session})


def ReportComponent(request, equipmentID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        eq = models.EquipmentMaster.objects.get(equipmentid=equipmentID)
        faci = models.Facility.objects.get(facilityid=eq.facilityid_id)
        si = models.Sites.objects.get(siteid=faci.siteid_id)
        data = models.ComponentMaster.objects.filter(equipmentid=equipmentID)
        pagiComp = Paginator(data, 25)
        pageComp = request.GET.get('page', 1)
        try:
            obj = pagiComp.page(pageComp)
        except PageNotAnInteger:
            obj = pagiComp.page(1)
        except EmptyPage:
            obj = pageComp.page(pagiComp.num_pages)
    except:
        raise Http404
    return render(request, 'ManagerUI/Report_Component.html',
                  {'page': 'reportcomponent', 'obj': obj, 'equipmentID': equipmentID, 'facilityID': eq.facilityid_id,
                   'eq': eq, 'faci': faci, 'si': si, 'count': count, 'noti': noti, 'countnoti': countnoti,
                   'info': request.session})
def Mitigation(request,siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    return render(request, 'ManagerUI/Mitigation.html',
                  {'page': 'mitigation','siteID': siteID, 'count': count, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})

def MitigationSite(request,siteID):
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    tank = [8, 9, 12, 13, 14, 15]
    RecommendProposalTank = []
    RecommendProposalNormal = []
    APINormal = []
    APITank = []
    rwComponent = models.ComponentMaster.objects.all()
    rwdamAll = models.RwDamageMechanism.objects.all()
    rwassessment = models.RwAssessment.objects.all()
    datarw = []  # kiem tra id proposal co ton tai trong bang RwDamageMechanism
    for a in rwdamAll:
        array = a.id_dm_id
        datarw.append(array)
    for a in rwComponent:
        print("let go")
        data = []
        datamax = []
        if a.componenttypeid_id in tank:
            rwAsessmentT = models.RwAssessment.objects.filter(componentid_id=a.componentid)
            if rwAsessmentT.count() == 1:
                R1 = models.RwAssessment.objects.get(componentid_id=a.componentid)
                RecommendProposalTank.append(R1.id)
            elif rwAsessmentT.count() > 1:
                for b in rwAsessmentT:
                    if b.assessmentdate:
                        obj = {}
                        obj['assessmentdate'] = b.assessmentdate.timestamp()
                        obj['IDProposal'] = b.id
                        data.append(obj)
                        datamax.append(b.assessmentdate.timestamp())
                M = max(datamax)
                i = datamax.index(M)
                RecommendProposalTank.append(data[i]['IDProposal'])
        else:
            rwAsessmentN = models.RwAssessment.objects.filter(componentid_id=a.componentid)
            if rwAsessmentN.count() == 1:
                R1 = models.RwAssessment.objects.get(componentid_id=a.componentid)
                RecommendProposalNormal.append(R1.id)
            elif rwAsessmentN.count() > 1:
                for b in rwAsessmentN:
                    if b.assessmentdate:
                        obj = {}
                        obj['assessmentdate'] = b.assessmentdate.timestamp()
                        obj['IDProposal'] = b.id
                        data.append(obj)
                        datamax.append(b.assessmentdate.timestamp())
                M = max(datamax)
                i = datamax.index(M)
                RecommendProposalNormal.append(data[i]['IDProposal'])
    for nor in RecommendProposalNormal:
        rwasessmentN = models.RwAssessment.objects.get(id=nor)
        equipmaster = models.EquipmentMaster.objects.get(equipmentid=rwasessmentN.equipmentid_id)
        component = models.ComponentMaster.objects.get(componentid=rwasessmentN.componentid_id)
        equiptype = models.EquipmentType.objects.get(equipmenttypeid=equipmaster.equipmenttypeid_id)
        comptype = models.ComponentType.objects.get(componenttypeid=component.componenttypeid_id)
        faci = models.Facility.objects.get(facilityid=equipmaster.facilityid_id)
        site = models.Sites.objects.get(siteid=equipmaster.siteid_id)
        df = models.RwFullPof.objects.filter(id=nor)
        ca = models.RwFullFcof.objects.filter(id=nor)
        if df.count() > 0 and ca.count() > 0:
            df = models.RwFullPof.objects.get(id=nor)
            ca = models.RwFullFcof.objects.get(id=nor)
            obj = {}
            obj['ID'] = nor
            obj['API1'] = location.locatData(df.totaldfap1, ca.fcofvalue)
            obj['API2'] = location.locatData(df.totaldfap2, ca.fcofvalue)
            obj['API3'] = location.locatData(df.totaldfap3, ca.fcofvalue)
            obj['ConponentNumber'] = component.componentnumber
            obj['EquipmentNumber'] = equipmaster.equipmentnumber
            obj['Facility'] = faci.facilityname
            obj['Site'] = site.sitename
            obj['POFAPI1'] = df.pofap1category + ca.fcofcategory
            obj['POFAPI2'] = df.pofap2category + ca.fcofcategory
            obj['POFAPI3'] = df.pofap3category + ca.fcofcategory
            obj['RLI'] = df.rli
            obj['AssessmentName'] = rwasessmentN.proposalname
            obj['AssessmentDate'] = rwasessmentN.assessmentdate
            obj['CommissionDate'] = equipmaster.commissiondate
            obj['RiskAnalysisPeriod'] = rwasessmentN.riskanalysisperiod
            obj['EquipmentType'] = equiptype.equipmenttypename
            obj['ComponentType'] = comptype.componenttypename
            if (nor in datarw):
                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=nor)
                obj['InspectionDueDate'] = rwdam.inspduedate
            else:
                obj['InspectionDueDate'] = "None"
            APINormal.append(obj)
    for nor in RecommendProposalTank:
        rwasessmentN = models.RwAssessment.objects.get(id=nor)
        equipmaster = models.EquipmentMaster.objects.get(equipmentid=rwasessmentN.equipmentid_id)
        component = models.ComponentMaster.objects.get(componentid=rwasessmentN.componentid_id)
        equiptype = models.EquipmentType.objects.get(equipmenttypeid=equipmaster.equipmenttypeid_id)
        comptype = models.ComponentType.objects.get(componenttypeid=component.componenttypeid_id)
        faci = models.Facility.objects.get(facilityid=equipmaster.facilityid_id)
        site = models.Sites.objects.get(siteid=equipmaster.siteid_id)
        df = models.RwFullPof.objects.filter(id=nor)
        ca = models.RwFullFcof.objects.filter(id=nor)
        if df.count() > 0 and ca.count() > 0:
            df = models.RwFullPof.objects.get(id=nor)
            ca = models.RwFullFcof.objects.get(id=nor)
            obj = {}
            obj['ID'] = nor
            obj['API1'] = location.locatData(df.totaldfap1, ca.fcofvalue)
            obj['API2'] = location.locatData(df.totaldfap2, ca.fcofvalue)
            obj['API3'] = location.locatData(df.totaldfap3, ca.fcofvalue)
            obj['ComponentNumber'] = component.componentnumber
            obj['EquipmentNumber'] = equipmaster.equipmentnumber
            obj['Facility'] = faci.facilityname
            obj['Site'] = site.sitename
            obj['POFAPI1'] = df.pofap1category + ca.fcofcategory
            obj['POFAPI2'] = df.pofap2category + ca.fcofcategory
            obj['POFAPI3'] = df.pofap3category + ca.fcofcategory
            obj['RLI'] = df.rli
            obj['AssessmentName'] = rwasessmentN.proposalname
            obj['AssessmentDate'] = rwasessmentN.assessmentdate
            obj['CommissionDate'] = equipmaster.commissiondate
            obj['RiskAnalysisPeriod'] = rwasessmentN.riskanalysisperiod
            obj['EquipmentType'] = equiptype.equipmenttypename
            obj['ComponentType'] = comptype.componenttypename
            if (nor in datarw):
                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=nor)
                obj['InspectionDueDate'] = rwdam.inspduedate
            else:
                obj['InspectionDueDate'] = "None"
            APITank.append(obj)
    try:
        if '_detail' in request.POST:
            for a in rwassessment:
                if request.POST.get('%d' % a.id):
                    return redirect('damgeFactor', proposalID=a.id)
        if '_refresh' in request.POST:
            return redirect('mitigationSite', siteID=siteID)
        if '_mitigation' in request.POST:
            for a in rwassessment:
                if request.POST.get('%d' % a.id):
                    return redirect('damageDetailmitigation', siteID=siteID,proposalID=a.id)
    except Exception as e:
        print(e)
    return render(request, 'FacilityUI/mitigation/mitigationSite.html',
                  {'page': 'mitigation','siteID':siteID,'APINormal':APINormal,'APITank':APITank, 'count': count, 'noti': noti,
                   'countnoti': countnoti, 'info': request.session})

def MitigationDetail(request, siteID,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    rwdamage= models.RwDamageMechanism.objects.get(id_dm_id=proposalID)
    dmitem = models.DMItems.objects.get(dmitemid=rwdamage.dmitemid_id)
    return render(request, 'FacilityUI/mitigation/damageMechanism.html',
                  {'page': 'damageDetailmitigation','siteID':siteID, 'count': count,
                   'noti': noti,
                   'countnoti': countnoti, 'info': request.session})
def FullyDamageFactor(request, proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        df = models.RwFullPof.objects.get(id= proposalID)
        rwAss = models.RwAssessment.objects.get(id= proposalID)
        data={}
        component = models.ComponentMaster.objects.get(componentid=rwAss.componentid_id)
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 12 or component.componenttypeid_id == 14 or component.componenttypeid_id == 15:
            isTank = 1
        else:
            isTank = 0
        if component.componenttypeid_id == 8 or component.componenttypeid_id == 14:
            isShell = 1
        else:
            isShell = 0
        data['thinningType'] = df.thinningtype
        data['gfftotal'] = df.gfftotal
        data['fms'] = df.fms
        data['thinningap1'] = roundData.roundDF(df.thinningap1)
        data['thinningap2'] = roundData.roundDF(df.thinningap2)
        data['thinningap3'] = roundData.roundDF(df.thinningap3)
        data['sccap1'] = roundData.roundDF(df.sccap1)
        data['sccap2'] = roundData.roundDF(df.sccap2)
        data['sccap3'] = roundData.roundDF(df.sccap3)
        data['externalap1'] = roundData.roundDF(df.externalap1)
        data['externalap2'] = roundData.roundDF(df.externalap2)
        data['externalap3'] = roundData.roundDF(df.externalap3)
        data['htha_ap1'] = roundData.roundDF(df.htha_ap1)
        data['htha_ap2'] = roundData.roundDF(df.htha_ap2)
        data['htha_ap3'] = roundData.roundDF(df.htha_ap3)
        data['brittleap1'] = roundData.roundDF(df.brittleap1)
        data['brittleap2'] = roundData.roundDF(df.brittleap2)
        data['brittleap3'] = roundData.roundDF(df.brittleap3)
        data['fatigueap1'] = roundData.roundDF(df.fatigueap1)
        data['fatigueap2'] = roundData.roundDF(df.fatigueap2)
        data['fatigueap3'] = roundData.roundDF(df.fatigueap3)
        data['thinninggeneralap1'] = roundData.roundDF(df.thinninggeneralap1)
        data['thinninggeneralap2'] = roundData.roundDF(df.thinninggeneralap2)
        data['thinninggeneralap3'] = roundData.roundDF(df.thinninggeneralap3)
        data['thinninglocalap1'] = roundData.roundDF(df.thinninglocalap1)
        data['thinninglocalap2'] = roundData.roundDF(df.thinninglocalap2)
        data['thinninglocalap3'] = roundData.roundDF(df.thinninglocalap3)
        data['totaldfap1'] = roundData.roundDF(df.totaldfap1)
        data['totaldfap2'] = roundData.roundDF(df.totaldfap2)
        data['totaldfap3'] = roundData.roundDF(df.totaldfap3)
        data['pofap1'] = roundData.roundPoF(df.pofap1)
        data['pofap2'] = roundData.roundPoF(df.pofap2)
        data['pofap3'] = roundData.roundPoF(df.pofap3)
        data['pofap1category'] = df.pofap1category
        data['pofap2category'] = df.pofap2category
        data['pofap3category'] = df.pofap3category
        if '_btnGoverningExternal' in request.POST:
            return redirect('governingExternal', proposalID=proposalID)
        if '_btnThinning' in request.POST:
            return redirect('choseThining', proposalID=proposalID)
        if request.method == 'POST':
            df.thinningtype = request.POST.get('thinningType')
            df.save()
            ReCalculate.ReCalculate(proposalID)
            return redirect('damgeFactor', proposalID)
    except Exception as e:
        print(e)
        raise Http404
    return render(request, 'FacilityUI/risk_summary/dfFull.html', {'page':'damageFactor', 'obj':data, 'assess': rwAss, 'isTank': isTank,
                                                                   'isShell': isShell, 'proposalID':proposalID,'info':request.session,'noti':noti,'countnoti':countnoti,'count':count})
def chooseThining(request,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    if '_thin' in request.POST:
        return redirect('thining', proposalID=proposalID)
    if '_lining' in request.POST:
        return redirect('lining', proposalID=proposalID)
    return render(request,'FacilityUI/risk_summary/chooseThining.html',{'page':'chooseThining','proposalID':proposalID,'noti':noti,'countnoti':countnoti,'count':count})
def showLining(request,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'FacilityUI/risk_summary/showLining.html',
                  {'page': 'lining', 'proposalID': proposalID, 'info': request.session, 'noti': noti,
                   'countnoti': countnoti, 'count': count})
def ShowThining(request,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    try:
        data = []
        rwcomponent = models.RwComponent.objects.get(id=proposalID)
        rwassessment = models.RwAssessment.objects.get(id=proposalID)
        rwcoat = models.RwCoating.objects.get(id=proposalID)
        rwmaterial = models.RwMaterial.objects.get(id=proposalID)
        rwequipment = models.RwEquipment.objects.get(id=proposalID)
        damageMachinsm = models.RwDamageMechanism.objects.get(id_dm=proposalID)
        comp = models.ComponentMaster.objects.get(componentid=rwassessment.componentid_id)
        comptype = models.ComponentType.objects.get(componenttypeid=comp.componenttypeid_id)
        EquipmentType = models.EquipmentType.objects.get(
            equipmenttypeid=models.EquipmentMaster.objects.get(
                equipmentid=comp.equipmentid_id).equipmenttypeid_id).equipmenttypename
        COMPONENT_INSTALL_DATE = models.EquipmentMaster.objects.get(
            equipmentid=comp.equipmentid_id).commissiondate
        ComponentNumber = str(comp.componentnumber)
        APIComponentType = models.ApiComponentType.objects.get(
            apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename
        obj = {}
        obj['AllowableStress'] = rwcomponent.allowablestress
        obj['MinimunRequiredThickness'] = rwcomponent.minreqthickness
        obj['WeltJointEfficiency'] = rwcomponent.weldjointefficiency
        obj['CorrosionRate'] = rwcomponent.currentcorrosionrate
        obj['Diameter'] = rwcomponent.nominaldiameter
        obj['NominalThickness'] = rwcomponent.nominalthickness
        obj['CurentThickness'] = rwcomponent.currentthickness
        obj['ChemicalInjection'] = rwcomponent.chemicalinjection
        obj['HighlyEffectiveInspectionforChemicalInjection'] = rwcomponent.highlyinjectioninsp
        obj['assessmentDate'] = rwassessment.assessmentdate
        obj['InternalCladding'] = rwcoat.internalcladding
        obj['CladdingCorrosionRate'] = rwcoat.claddingcorrosionrate
        obj['YeildStrength'] = rwmaterial.yieldstrength
        obj['TensileStrength'] = rwmaterial.tensilestrength
        obj['DesignPressure'] = rwmaterial.designpressure
        obj['Onlinemonitoring'] = rwequipment.onlinemonitoring
        obj['HighEffectiveDeadlegs'] = rwequipment.highlydeadleginsp
        obj['LastInspectionDate']=damageMachinsm.lastinspdate
        obj['NumberofInspection']=damageMachinsm.numberofinspections
        obj['shapeFactor']=comptype.shapefactor
        obj['shape']=API_COMPONENT_TYPE_NAME=models.ApiComponentType.objects.get(
                                            apicomponenttypeid=comp.apicomponenttypeid).apicomponenttypename

        thin = Detail_DM_CAL.Df_Thin(obj['Diameter'],obj['NominalThickness'],obj['CurentThickness'],obj['MinimunRequiredThickness'],obj['CorrosionRate'],
                                     rwmaterial.corrosionallowance,bool(rwcomponent.releasepreventionbarrier),rwcoat.claddingcorrosionrate,bool(rwcoat.internalcladding),
                                     0,"E",obj['Onlinemonitoring'],obj['HighEffectiveDeadlegs'],bool(rwequipment.containsdeadlegs),rwequipment.tankismaintained,
                                     rwequipment.adjustmentsettle,rwequipment.componentiswelded,obj['WeltJointEfficiency'],obj['AllowableStress'],obj['TensileStrength'],obj['YeildStrength'],rwcomponent.structuralthickness,
                                     rwcomponent.minstructuralthickness,rwmaterial.designpressure,comptype.shapefactor,rwcomponent.confidencecorrosionrate,EquipmentType,rwassessment.assessmentdate,COMPONENT_INSTALL_DATE,ComponentNumber,APIComponentType)
        obj['flowTress']=thin.FS_Thin
        obj['strengthRatioIn']=thin.strengthRatioInter
        obj['strengthRatioMin']=thin.strengthRationMin
        obj['adjustmentInjection']=thin.adjustmentInjection
        obj['adjustmentOnline']=thin.adjustmentOnline
        obj['adjustmentDeadLegs']=thin.adjustmentDeadLegs

        obj['priorProbabilities1']=thin.Pr_P1_Thin
        obj['priorProbabilities2']=thin.Pr_P2_Thin
        obj['priorProbabilities3']=thin.Pr_P3_Thin
        obj['inspectioneffectivenessfactors1']=thin.I1_Thin()
        obj['inspectioneffectivenessfactors2']=thin.I2_Thin()
        obj['inspectioneffectivenessfactors3']=thin.I3_Thin()
        obj['PosteriorProbability1']=thin.Po_P1_Thin()
        obj['PosteriorProbability2']=thin.Po_P2_Thin()
        obj['PosteriorProbability3']=thin.Po_P3_Thin()
        obj['BetaReliabilityIndices0AP_1']=thin.B1_Thin(0)
        obj['BetaReliabilityIndices0AP_2']=thin.B1_Thin(36)
        obj['BetaReliabilityIndices0AP_3']=thin.B1_Thin(72)
        obj['BetaReliabilityIndices1AP_1'] = thin.B2_Thin(0)
        obj['BetaReliabilityIndices1AP_2'] = thin.B2_Thin(36)
        obj['BetaReliabilityIndices1AP_3'] = thin.B2_Thin(72)
        obj['BetaReliabilityIndices2AP_1'] = thin.B3_Thin(0)
        obj['BetaReliabilityIndices2AP_2'] = thin.B3_Thin(36)
        obj['BetaReliabilityIndices2AP_3'] = thin.B3_Thin(72)
        obj['age1']=thin.agetk(0)
        obj['age2']=thin.agetk(36)
        obj['age3']=thin.agetk(72)
        obj['agetk1']=thin.agetk(0)
        obj['agetk2']=thin.agetk(36)
        obj['agetk3']=thin.agetk(72)
        obj['agerc']=thin.agerc()
        obj['ArtWithout1']=thin.ArtWithoutCladdingMaterial(0)
        obj['ArtWithout2']=thin.ArtWithoutCladdingMaterial(36)
        obj['ArtWithout3']=thin.ArtWithoutCladdingMaterial(72)
        obj['ArtWith1_1']=thin.ArtWithCladdingMaterial1(0)
        obj['ArtWith1_2']=thin.ArtWithCladdingMaterial1(36)
        obj['ArtWith1_3']=thin.ArtWithCladdingMaterial1(72)
        obj['ArtWith2_1'] = thin.ArtWithCladdingMaterial2(0)
        obj['ArtWith2_2'] = thin.ArtWithCladdingMaterial2(36)
        obj['ArtWith2_3'] = thin.ArtWithCladdingMaterial2(72)
        obj['WallLossFraction1'] = thin.Art(0)
        obj['WallLossFraction2'] = thin.Art(36)
        obj['WallLossFraction3'] = thin.Art(72)

        obj['BaseDamageFactor1'] = thin.DFB_THIN_API(0)
        obj['BaseDamageFactor2'] = thin.DFB_THIN_API(36)
        obj['BaseDamageFactor3'] = thin.DFB_THIN_API(72)
        obj['ThinningDamageFactor1'] = thin.DF_THINNING_API(0)
        obj['ThinningDamageFactor2'] = thin.DF_THINNING_API(36)
        obj['ThinningDamageFactor3'] = thin.DF_THINNING_API(72)


         # test Linning
        lining=Detail_DM_CAL.Df_Lining(bool(rwcoat.internallining),rwcoat.internallinertype,rwcoat.internallinercondition,bool(rwequipment.lineronlinemonitoring),rwassessment.assessmentdate,COMPONENT_INSTALL_DATE,"")
        print(lining.DF_LINNING(3))
        # data.append(obj)
        # data.append(output)

        # if 'BaseMetalThickness' in request.POST:
        #     return redirect('governingExternal', proposalID=proposalID)
        # else:
        #     print("BaseMetalThickness")
        return render(request, 'FacilityUI/risk_summary/showThining.html',{'page':'thining','proposalID':proposalID,'a':obj,'info':request.session,'noti':noti,'countnoti':countnoti,'count':count})
    except Exception as e:
        print(e)
        raise Http404

def ShowGoverningExternal(request,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'FacilityUI/risk_summary/showGoverningExternal.html',{'page':'governingExternal','info':request.session,'noti':noti,'countnoti':countnoti,'count':count})
def ShowGoverning(request,proposalID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'FacilityUI/risk_summary/showGoverning.html',{'page':'governing','info':request.session,'noti':noti,'countnoti':countnoti,'count':count})
def CalculateFunctionManager(request,siteID):
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()

    tank = [8,9,12,13,14,15]
    RecommendProposalTank = []
    RecommendProposalNormal = []
    APINormal = []
    APITank = []
    rwComponent = models.ComponentMaster.objects.all()
    rwdamAll = models.RwDamageMechanism.objects.all()
    rwassessment = models.RwAssessment.objects.all()
    datarw = []  # kiem tra id proposal co ton tai trong bang RwDamageMechanism
    for a in rwdamAll:
        array = a.id_dm_id
        datarw.append(array)
    for a in rwComponent:
        data = []
        datamax =[]
        if a.componenttypeid_id in tank:
            rwAsessmentT = models.RwAssessment.objects.filter(componentid_id = a.componentid)
            if rwAsessmentT.count() ==1:
                R1 = models.RwAssessment.objects.get(componentid_id = a.componentid)
                RecommendProposalTank.append(R1.id)
            elif rwAsessmentT.count() > 1 :
                for b in rwAsessmentT:
                    if b.assessmentdate:
                        obj={}
                        obj['assessmentdate']= b.assessmentdate.timestamp()
                        obj['IDProposal'] = b.id
                        data.append(obj)
                        datamax.append(b.assessmentdate.timestamp())
                M = max(datamax)
                i = datamax.index(M)
                RecommendProposalTank.append(data[i]['IDProposal'])
        else:
            rwAsessmentN = models.RwAssessment.objects.filter(componentid_id=a.componentid)
            if rwAsessmentN.count() == 1:
                R1 = models.RwAssessment.objects.get(componentid_id=a.componentid)
                RecommendProposalNormal.append(R1.id)
            elif rwAsessmentN.count() > 1:
                for b in rwAsessmentN:
                    if b.assessmentdate:
                        obj = {}
                        obj['assessmentdate'] = b.assessmentdate.timestamp()
                        obj['IDProposal'] = b.id
                        data.append(obj)
                        datamax.append(b.assessmentdate.timestamp())
                M = max(datamax)
                i = datamax.index(M)
                RecommendProposalNormal.append(data[i]['IDProposal'])
    for nor in RecommendProposalNormal:
        rwasessmentN = models.RwAssessment.objects.get(id=nor)
        equipmaster = models.EquipmentMaster.objects.get(equipmentid=rwasessmentN.equipmentid_id)
        component = models.ComponentMaster.objects.get(componentid=rwasessmentN.componentid_id)
        equiptype = models.EquipmentType.objects.get(equipmenttypeid=equipmaster.equipmenttypeid_id)
        comptype = models.ComponentType.objects.get(componenttypeid=component.componenttypeid_id)
        faci = models.Facility.objects.get(facilityid=equipmaster.facilityid_id)
        site = models.Sites.objects.get(siteid=equipmaster.siteid_id)
        df = models.RwFullPof.objects.filter(id=nor)
        ca = models.RwFullFcof.objects.filter(id=nor)
        if df.count() > 0 and ca.count() > 0:
            df = models.RwFullPof.objects.get(id=nor)
            ca = models.RwFullFcof.objects.get(id=nor)
            obj = {}
            obj['ID'] = nor
            obj['API1'] = location.locatData(df.totaldfap1, ca.fcofvalue)
            obj['API2'] = location.locatData(df.totaldfap2, ca.fcofvalue)
            obj['API3'] = location.locatData(df.totaldfap3, ca.fcofvalue)
            obj['ConponentNumber'] = component.componentnumber
            obj['EquipmentNumber'] = equipmaster.equipmentnumber
            obj['Facility'] = faci.facilityname
            obj['Site'] = site.sitename
            obj['POFAPI1'] = df.pofap1category + ca.fcofcategory
            obj['POFAPI2'] = df.pofap2category + ca.fcofcategory
            obj['POFAPI3'] = df.pofap3category + ca.fcofcategory
            obj['RLI'] = df.rli
            obj['AssessmentName'] = rwasessmentN.proposalname
            obj['AssessmentDate'] = rwasessmentN.assessmentdate
            obj['CommissionDate'] = equipmaster.commissiondate
            obj['RiskAnalysisPeriod'] = rwasessmentN.riskanalysisperiod
            obj['EquipmentType'] = equiptype.equipmenttypename
            obj['ComponentType'] = comptype.componenttypename
            if (nor in datarw):
                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=nor)
                obj['InspectionDueDate'] = rwdam.inspduedate
            else:
                obj['InspectionDueDate'] = "None"
            APINormal.append(obj)
    for nor in RecommendProposalTank:
        rwasessmentN = models.RwAssessment.objects.get(id=nor)
        equipmaster = models.EquipmentMaster.objects.get(equipmentid=rwasessmentN.equipmentid_id)
        component = models.ComponentMaster.objects.get(componentid=rwasessmentN.componentid_id)
        equiptype = models.EquipmentType.objects.get(equipmenttypeid=equipmaster.equipmenttypeid_id)
        comptype = models.ComponentType.objects.get(componenttypeid=component.componenttypeid_id)
        faci = models.Facility.objects.get(facilityid=equipmaster.facilityid_id)
        site = models.Sites.objects.get(siteid=equipmaster.siteid_id)
        df = models.RwFullPof.objects.filter(id=nor)
        ca = models.RwFullFcof.objects.filter(id=nor)
        if df.count() > 0 and ca.count() > 0:
            df = models.RwFullPof.objects.get(id=nor)
            ca = models.RwFullFcof.objects.get(id=nor)
            obj = {}
            obj['ID'] = nor
            obj['API1'] = location.locatData(df.totaldfap1, ca.fcofvalue)
            obj['API2'] = location.locatData(df.totaldfap2, ca.fcofvalue)
            obj['API3'] = location.locatData(df.totaldfap3, ca.fcofvalue)
            obj['ComponentNumber'] = component.componentnumber
            obj['EquipmentNumber'] = equipmaster.equipmentnumber
            obj['Facility'] = faci.facilityname
            obj['Site'] = site.sitename
            obj['POFAPI1'] = df.pofap1category + ca.fcofcategory
            obj['POFAPI2'] = df.pofap2category + ca.fcofcategory
            obj['POFAPI3'] = df.pofap3category + ca.fcofcategory
            obj['RLI'] = df.rli
            obj['AssessmentName'] = rwasessmentN.proposalname
            obj['AssessmentDate'] = rwasessmentN.assessmentdate
            obj['CommissionDate'] = equipmaster.commissiondate
            obj['RiskAnalysisPeriod'] = rwasessmentN.riskanalysisperiod
            obj['EquipmentType'] = equiptype.equipmenttypename
            obj['ComponentType'] = comptype.componenttypename
            if (nor in datarw):
                rwdam = models.RwDamageMechanism.objects.get(id_dm_id=nor)
                obj['InspectionDueDate'] = rwdam.inspduedate
            else:
                obj['InspectionDueDate'] = "None"
            APITank.append(obj)
    try:
        if '_detail' in request.POST:
            for a in rwassessment:
                if request.POST.get('%d' % a.id):
                    return redirect('damgeFactorMana', proposalID=a.id)
        if '_refresh' in request.POST:
            return redirect('calculateFunctionManager', siteID=siteID)
    except Exception as e:
        print(e)

    return render(request, 'ManagerUI/Calculate_Function_Manager.html', {'page':'calculateFunctionManager','siteID':siteID,'APINormal':APINormal,'APITank':APITank,'info':request.session,'noti':noti,'countnoti':countnoti,'count':count})
def Help_UseSoftware(request):
    countveri = 0
    noti = models.ZNotification.objects.all().filter(id_user=request.session['id'])
    countnoti = noti.filter(state=0).count()
    count = models.Emailto.objects.filter(Q(Emailt=models.ZUser.objects.filter(id=request.session['id'])[0].email),
                                          Q(Is_see=0)).count()
    return render(request, 'help/helpusesoft.html',
                  {'page': 'userManual', 'info': request.session, 'count': count, 'noti': noti, 'countnoti': countnoti})

def ViewExeclProposal(request, index, type):
    componentID=models.RwAssessment.objects.get(id=index).componentid
    getP_risk=export_data.getP_risk(index)
    getP_insp=export_data.getP_insp_show(index)
    getP_name=export_data.getP_name(index)
    if getP_risk['init_thinning']==0 or getP_risk['init_thinning'] is None:
        getP_risk['init_thinningcv']='N/A'
    elif getP_risk['init_thinning'] <=2:
        getP_risk['init_thinningcv']='A'
    elif getP_risk['init_thinning'] <=20:
        getP_risk['init_thinningcv']='B'
    elif getP_risk['init_thinning'] <=100:
        getP_risk['init_thinningcv']='C'
    elif getP_risk['init_thinning'] <1000:
        getP_risk['init_thinningcv']='D'
    else:
        getP_risk['init_thinningcv']='E'

    if getP_risk['init_cracking']==0 or getP_risk['init_cracking'] is None:
        getP_risk['init_crackingcvv']='N/A'
    elif getP_risk['init_cracking'] <=2:
        getP_risk['init_crackingcv']='A'
    elif getP_risk['init_cracking'] <=20:
        getP_risk['init_crackingcv']='B'
    elif getP_risk['init_cracking'] <=100:
        getP_risk['init_crackingcv']='C'
    elif getP_risk['init_cracking'] <1000:
        getP_risk['init_crackingcv']='D'
    else:
        getP_risk['init_crackingcv']='E'

    if getP_risk['init_other']==0 or getP_risk['init_other'] is None:
        getP_risk['init_othercv']='N/A'
    elif getP_risk['init_other'] <=2:
        getP_risk['init_othercv']='A'
    elif getP_risk['init_other'] <=20:
        getP_risk['init_othercv']='B'
    elif getP_risk['init_other'] <=100:
        getP_risk['init_othercv']='C'
    elif getP_risk['init_other'] <1000:
        getP_risk['init_othercv']='D'
    else:
        getP_risk['init_othercv']='E'

    if getP_risk['init_pof']==0 or getP_risk['init_pof'] is None:
        getP_risk['init_pofcv']='N/A'
    elif getP_risk['init_pof'] <=2:
        getP_risk['init_pofcv']='A'
    elif getP_risk['init_pof'] <=20:
        getP_risk['init_pofcv']='B'
    elif getP_risk['init_pof'] <=100:
        getP_risk['init_pofcv']='C'
    elif getP_risk['init_pof'] <1000:
        getP_risk['init_pofcv']='D'
    else:
        getP_risk['init_pofcv']='E'

    if getP_risk['ext_thinning']==0 or getP_risk['ext_thinning'] is None:
        getP_risk['ext_thinningcv']='N/A'
    elif getP_risk['ext_thinning'] <=2:
        getP_risk['ext_thinningcv']='A'
    elif getP_risk['ext_thinning'] <=20:
        getP_risk['ext_thinningcv']='B'
    elif getP_risk['ext_thinning'] <=100:
        getP_risk['ext_thinningcv']='C'
    elif getP_risk['ext_thinning'] <1000:
        getP_risk['ext_thinningcv']='D'
    else:
        getP_risk['ext_thinningcv']='E'

    if getP_risk['pof_catalog']==0 or getP_risk['pof_catalog'] is None:
        getP_risk['pof_catalogcv']='N/A'
    elif getP_risk['pof_catalog'] <=2:
        getP_risk['pof_catalogcv']='A'
    elif getP_risk['pof_catalog'] <=20:
        getP_risk['pof_catalogcv']='B'
    elif getP_risk['pof_catalog'] <=100:
        getP_risk['pof_catalogcv']='C'
    elif getP_risk['pof_catalog'] <1000:
        getP_risk['pof_catalogcv']='D'
    else:
        getP_risk['pof_catalogcv']='E'

    if getP_risk['flamable']==0 or getP_risk['flamable'] is None:
        getP_risk['flamablecv']=0
    elif getP_risk['flamable'] <=10000:
        getP_risk['flamablecv']=1
    elif getP_risk['flamable'] <=100000:
        getP_risk['flamablecv']=2
    elif getP_risk['flamable'] <=1000000:
        getP_risk['flamablecv']=3
    elif getP_risk['flamable'] <10000000:
        getP_risk['flamablecv']=4
    else:
        getP_risk['flamablecv']=5

    if getP_risk['inj']==0 or getP_risk['inj'] is None:
        getP_risk['injcv']=0
    elif getP_risk['inj'] <=10000:
        getP_risk['injcv']=1
    elif getP_risk['inj'] <=100000:
        getP_risk['injcv']=2
    elif getP_risk['inj'] <=1000000:
        getP_risk['injcv']=3
    elif getP_risk['inj'] <10000000:
        getP_risk['injcv']=4
    else:
        getP_risk['injcv']=5

    if getP_risk['business']==0 or getP_risk['business'] is None:
        getP_risk['businesscv']=0
    elif getP_risk['business'] <=10000:
        getP_risk['businesscv']=1
    elif getP_risk['business'] <=100000:
        getP_risk['businesscv']=2
    elif getP_risk['business'] <=1000000:
        getP_risk['businesscv']=3
    elif getP_risk['business'] <10000000:
        getP_risk['businesscv']=4
    else:
        getP_risk['businesscv']=5

    if getP_risk['env']==0 or getP_risk['env'] is None:
        getP_risk['envcv']=0
    elif getP_risk['env'] <=10000:
        getP_risk['envcv']=1
    elif getP_risk['env'] <=100000:
        getP_risk['envcv']=2
    elif getP_risk['env'] <=1000000:
        getP_risk['envcv']=3
    elif getP_risk['env'] <10000000:
        getP_risk['envcv']=4
    else:
        getP_risk['envcv']=5

    if getP_risk['consequence']==0 or getP_risk['consequence'] is None:
        getP_risk['consequencecv']=0
    elif getP_risk['consequence'] <=10000:
        getP_risk['consequencecv']=1
    elif getP_risk['consequence'] <=100000:
        getP_risk['consequencecv']=2
    elif getP_risk['consequence'] <=1000000:
        getP_risk['consequencecv']=3
    elif getP_risk['consequence'] <10000000:
        getP_risk['consequencecv']=4
    else:
        getP_risk['consequencecv']=5

    if getP_risk['consequence'] == 0 or getP_risk['pof_catalog'] == 'N/A':
        getP_risk['riskcv']= 'N/A'
    elif getP_risk['consequence'] in (1, 2) and getP_risk['pof_catalog'] in ('A', 'B', 'C'):
        getP_risk['riskcv'] = "Low"
    elif (getP_risk['consequence'] in (1, 2) and getP_risk['pof_catalog'] == 'D') or (getP_risk['consequence'] in (3, 4) and getP_risk['pof_catalog'] in ('A', 'B')) or (getP_risk['consequence'] == 3 and getP_risk['pof_catalog'] == 'C'):
        getP_risk['riskcv'] = "Medium"
    elif (getP_risk['consequence'] == 5 and getP_risk['pof_catalog'] in ('C', 'D', 'E')) or (getP_risk['consequence'] == 4 and getP_risk['pof_catalog'] == 'E'):
        getP_risk['riskcv'] = "High"
    else:
        getP_risk['riskcv'] = "Medium High"

    if getP_risk['consequence'] == 0 or getP_risk['pof_catalog2'] == 'N/A':
        getP_risk['risk_futurecv'] = 'N/A'
    elif getP_risk['consequence'] in (1, 2) and getP_risk['pof_catalog2'] in ('A', 'B', 'C'):
        getP_risk['risk_futurecv'] = "Low"
    elif (getP_risk['consequence'] in (1, 2) and getP_risk['pof_catalog2'] == 'D') or (getP_risk['consequence'] in (3, 4) and getP_risk['pof_catalog2'] in ('A', 'B')) or (getP_risk['consequence'] == 3 and getP_risk['pof_catalog2'] == 'C'):
        getP_risk['risk_futurecv'] = "Medium"
    elif (getP_risk['consequence'] == 5 and getP_risk['pof_catalog2'] in ('C', 'D', 'E')) or (getP_risk['consequence'] == 4 and getP_risk['pof_catalog2'] == 'E'):
        getP_risk['risk_futurecv'] = "High"
    else:
        getP_risk['risk_futurecv'] = "Medium High"
    return render(request, 'FacilityUI/proposal/proposal_excel.html' , {'page':'damageFactor', 'obj': getP_risk,'obj1':getP_insp, 'id':index, 'componentID':componentID} )

def DatabaseReport(request):
    return render(request,  'FacilityUI/showdatabase/database_report.html',{'page':'databasereport'})
def RBITracking(request):
    return render(request,  'FacilityUI/showdatabase/RBITracking.html',{'page':'rbitracking'})