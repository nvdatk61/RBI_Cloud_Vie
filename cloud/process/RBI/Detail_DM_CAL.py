import time
import time
import math
import traceback#dung cho tinh toan noi suy
import sys#dung cho tinh toan noi suy
from builtins import property
from datetime import datetime
import  numpy as np
from dateutil.relativedelta import relativedelta
from pathlib import _Selector
#from rbi import MYSQL_CAL as DAL_CAL
# from pyglet.input.carbon_hid import Self

from cloud.process.RBI import Postgresql as DAL_CAL
from django.core.mail import EmailMessage
from cloud import models

class Df_Thin:
    def __init__(self,Diametter ,NomalThick ,CurrentThick,MinThickReq,CorrosionRate,CA,ProtectedBarrier,CladdingCorrosionRate,InternalCladding,
                 NoINSP_THINNING,EFF_THIN,OnlineMonitoring,HighlyEffectDeadleg,ContainsDeadlegs,TankMaintain653,AdjustmentSettle,ComponentIsWeld,
                 WeldJointEffciency,AllowableStress,TensileStrengthDesignTemp,YieldStrengthDesignTemp,StructuralThickness,MINIUM_STRUCTURAL_THICKNESS_GOVERS,
                 Pressure,ShapeFactor,CR_Confidents_Level,AssesmentDate = datetime.now(),Commissiondate = datetime.now(),ComponentNumber = "",APIComponentType=""):
        self.AssesmentDate = AssesmentDate
        self.Commissiondate = Commissiondate
        self.ComponentNumber = ComponentNumber
        self.APIComponentType = APIComponentType

        self.Diametter = Diametter
        self.NomalThick = NomalThick
        self.CurrentThick = CurrentThick
        self.MinThickReq = MinThickReq
        self.CorrosionRate = CorrosionRate
        self.CA = CA
        self.ProtectedBarrier = ProtectedBarrier
        self.CladdingCorrosionRate = CladdingCorrosionRate
        self.InternalCladding = InternalCladding
        self.NoINSP_THINNING = NoINSP_THINNING
        self.EFF_THIN = EFF_THIN
        self.OnlineMonitoring = OnlineMonitoring
        self.HighlyEffectDeadleg = HighlyEffectDeadleg
        self.ContainsDeadlegs = ContainsDeadlegs
        self.TankMaintain653 = TankMaintain653
        self.AdjustmentSettle = AdjustmentSettle
        self.ComponentIsWeld = ComponentIsWeld
        self.WeldJointEffciency = WeldJointEffciency
        self.AllowableStress = AllowableStress
        self.TensileStrengthDesignTemp = TensileStrengthDesignTemp
        self.YieldStrengthDesignTemp = YieldStrengthDesignTemp
        self.StructuralThickness = StructuralThickness
        self.MINIUM_STRUCTURAL_THICKNESS_GOVERS = MINIUM_STRUCTURAL_THICKNESS_GOVERS
        self.Pressure = Pressure
        self.ShapeFactor = ShapeFactor
        self.CR_Confidents_Level = CR_Confidents_Level

    def getTmin(self):
        if self.APIComponentType == "TANKBOTTOM0" or self.APIComponentType =="TANKROOFFLOAT0":
            if (self.ProtectedBarrier):
                #t = 2.54
                t=0.05
            else:
                #t = 1.27
                t=0.1
        else:
            t = self.MinThickReq
        return t

    def agetk(self,age):
        return age
    def trdi(self):
        return self.CurrentThick
    def agerc(self):
        try:
            return max(((self.trdi() - self.NomalThick) / self.CorrosionRate), 0)
        except:
            return 0
    def Art(self,age):
        try:
            if self.APIComponentType == "TANKBOTTOM0" or self.APIComponentType == "TANKROOFFLOAT0":
                # print("Art")
                # print(max((1-(self.trdi() - self.CorrosionRate * self.agetk(age)) / (self.getTmin() + self.CA)), 0.0))
                return max((1-(self.trdi() - self.CorrosionRate * self.agetk(age)) / (self.getTmin() + self.CA)), 0.0)
            elif (self.InternalCladding):
                if (self.agetk(age) < self.agerc()):
                    return (self.CladdingCorrosionRate * self.agetk(age)/ self.trdi())
                else:
                    a =(self.CladdingCorrosionRate * self.agerc() + self.CorrosionRate * (self.agetk(age) - self.agerc())) / self.trdi()
                    return (self.CladdingCorrosionRate * self.agerc() + self.CorrosionRate * (self.agetk(age) - self.agerc())) / self.trdi()
            else:
                if self.trdi()==0:
                    return 1;
                else:
                    return (self.CorrosionRate * self.agetk(age) / self.trdi())
        except Exception as e:
            print(e)
            return 1
    def FS_Thin(self):
        return ((self.YieldStrengthDesignTemp + self.TensileStrengthDesignTemp)/2) * self.WeldJointEffciency * 1.1
    def getalpha(self):
        return self.ShapeFactor
    def SRp_Thin(self):
        if self.MINIUM_STRUCTURAL_THICKNESS_GOVERS == False:
            return (self.Pressure * self.Diametter)/(self.getalpha() * self.FS_Thin() * self.trdi())
        else:
            # return (self.WeldJointEffciency * self.TensileStrengthDesignTemp * max(self.getTmin(),self.StructuralThickness))/(self.FS_Thin() * self.trdi())
            #return (self.WeldJointEffciency * self.TensileStrengthDesignTemp * max(self.getTmin(),self.StructuralThickness))/(self.FS_Thin() * self.YieldStrengthDesignTemp)
            return (self.WeldJointEffciency * self.AllowableStress * max(self.getTmin(),self.StructuralThickness)) / (self.FS_Thin() * self.trdi())
    def Pr_P1_Thin(self):
        if self.CR_Confidents_Level == "Low":
            return 0.5
        elif self.CR_Confidents_Level == "Medium":
            return 0.7
        else:
            return 0.8
    def Pr_P2_Thin(self):
        if self.CR_Confidents_Level == "Low":
            return 0.3
        elif self.CR_Confidents_Level == "Medium":
            return 0.2
        else:
            return 0.15
    def Pr_P3_Thin(self):
        if self.CR_Confidents_Level == "Low":
            return 0.2
        elif self.CR_Confidents_Level == "Medium":
            return 0.1
        else:
            return  0.05

    def NA_Thin(self):
        a = DAL_CAL.POSTGRESQL.GET_NUMBER_INSP_FOR_THIN_EFFA(self.ComponentNumber, self.DM_Name[0])
        return a
    def NB_Thin(self):
        b = DAL_CAL.POSTGRESQL.GET_NUMBER_INSP_FOR_THIN_EEFB(self.ComponentNumber, self.DM_Name[0])
        return b
    def NC_Thin(self):
        c = DAL_CAL.POSTGRESQL.GET_NUMBER_INSP_FOR_THIN_EEFC(self.ComponentNumber, self.DM_Name[0])
        return c
    def ND_Thin(self):
        d = DAL_CAL.POSTGRESQL.GET_NUMBER_INSP_FOR_THIN_EEFD(self.ComponentNumber, self.DM_Name[0])
        return d
    def I1_Thin(self):
        a=self.Pr_P1_Thin() * pow(0.9,self.NA_Thin()) * pow(0.7,self.NB_Thin()) * pow(0.5,self.NC_Thin()) * pow(0.4,self.ND_Thin())
        return self.Pr_P1_Thin() * pow(0.9,self.NA_Thin()) * pow(0.7,self.NB_Thin()) * pow(0.5,self.NC_Thin()) * pow(0.4,self.ND_Thin())
    def I2_Thin(self):
        a=self.Pr_P2_Thin() * pow(0.09,self.NA_Thin()) * pow(0.2,self.NB_Thin()) * pow(0.3,self.NC_Thin()) * pow(0.33,self.ND_Thin())
        return self.Pr_P2_Thin() * pow(0.09,self.NA_Thin()) * pow(0.2,self.NB_Thin()) * pow(0.3,self.NC_Thin()) * pow(0.33,self.ND_Thin())
    def I3_Thin(self):
        a=self.Pr_P3_Thin() * pow(0.01,self.NA_Thin()) * pow(0.1,self.NB_Thin()) * pow(0.2,self.NC_Thin()) * pow(0.27,self.ND_Thin())
        return self.Pr_P3_Thin() * pow(0.01,self.NA_Thin()) * pow(0.1,self.NB_Thin()) * pow(0.2,self.NC_Thin()) * pow(0.27,self.ND_Thin())
    def Po_P1_Thin(self):
        a=self.I1_Thin()/(self.I1_Thin() + self.I2_Thin() + self.I3_Thin())
        return self.I1_Thin()/(self.I1_Thin() + self.I2_Thin() + self.I3_Thin())
    def Po_P2_Thin(self):
        a = self.I2_Thin()/(self.I1_Thin() + self.I2_Thin() + self.I3_Thin())
        return self.I2_Thin()/(self.I1_Thin() + self.I2_Thin() + self.I3_Thin())
    def Po_P3_Thin(self):
        return self.I3_Thin()/(self.I1_Thin() + self.I2_Thin() + self.I3_Thin())
    def B1_Thin(self,age):
        return (1 - self.Art(age)- self.SRp_Thin())/math.sqrt(pow(self.Art(age), 2) * 0.04 + pow((1 - self.Art(age)), 2) * 0.04 + pow(self.SRp_Thin(), 2) * pow(0.05, 2))
    def B2_Thin(self,age):
        return (1- 2*self.Art(age)-self.SRp_Thin())/math.sqrt(pow(self.Art(age),2)*4*0.04 + pow(1-2*self.Art(age),2)*0.04+pow(self.SRp_Thin(),2)*pow(0.05,2))
    def B3_Thin(self,age):
        return (1- 4*self.Art(age)-self.SRp_Thin())/math.sqrt(pow(self.Art(age),2)*16*0.04 + pow(1-4*self.Art(age),2)*0.04+pow(self.SRp_Thin(),2)*pow(0.05,2))

    def API_ART(self, a):
        if self.APIComponentType == 'TANKBOTTOM0' or self.APIComponentType == 'TANKROOFFLOAT0':
            data = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
                    0.95, 1]
            if a < (data[0] + data[1]) / 2:
            #if 0.025 < a < (data[0] + data[1]) / 2:
                return data[0]
            elif (a < (data[1] + data[2]) / 2):
                return data[1]
            elif (a < (data[2] + data[3]) / 2):
                return data[2]
            elif (a < (data[3] + data[4]) / 2):
                return data[3]
            elif (a < (data[4] + data[5]) / 2):
                return data[4]
            elif (a < (data[5] + data[6]) / 2):
                return data[5]
            elif (a < (data[6] + data[7]) / 2):
                return data[6]
            elif (a < (data[7] + data[8]) / 2):
                return data[7]
            elif (a < (data[8] + data[9]) / 2):
                return data[8]
            elif (a < (data[9] + data[10]) / 2):
                return data[9]
            elif (a < (data[10] + data[11]) / 2):
                return data[10]
            elif (a < (data[11] + data[12]) / 2):
                return data[11]
            elif (a < (data[12] + data[13]) / 2):
                return data[12]
            elif (a < (data[13] + data[14]) / 2):
                return data[13]
            elif (a < (data[14] + data[15]) / 2):
                return data[14]
            elif (a < (data[15] + data[16]) / 2):
                return data[15]
            elif (a < (data[16] + data[17]) / 2):
                return data[16]
            elif (a < (data[17] + data[18]) / 2):
                return data[17]
            elif (a < (data[18] + data[19]) / 2):
                return data[18]
            else:
                return data[19]
        else:
            return a

    def erfcc(self,x):
        z = abs(x)
        t = 1. / (1. + 0.5 * z)
        r = t * math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (.37409196 +
                                                                      t * (.09678418 + t * (-.18628806 + t * (.27886807 +
                                                                                                         t * (
                                                                                                         -1.13520398 + t * (
                                                                                                         1.48851587 + t * (
                                                                                                         -.82215223 +
                                                                                                         t * .17087277)))))))))
        if (x >= 0.):
            return r
        else:
            return 2. - r

    def ncdf(self,x):
        return 1. - 0.5 * math.erfc(x / (2 ** 0.5))
    def DFB_THIN(self, age):
        self.EFF_THIN = DAL_CAL.POSTGRESQL.GET_MAX_INSP(self.ComponentNumber, self.DM_Name[0])
        self.NoINSP_THINNING = DAL_CAL.POSTGRESQL.GET_NUMBER_INSP(self.ComponentNumber,self.DM_Name[0])
        if (self.APIComponentType == 'TANKBOTTOM0' or self.APIComponentType == 'TANKROOFFLOAT0'):
            if (self.NomalThick == 0 or self.CurrentThick == 0):
                return 1390
            else:
                return DAL_CAL.POSTGRESQL.GET_TBL_512(self.API_ART(self.Art(age)), self.NoINSP_THINNING, self.EFF_THIN)
                #return DAL_CAL.POSTGRESQL.GET_TBL_512(self.API_ART(self.Art(age)), self.EFF_THIN)
        else:
            try:
                if (self.NomalThick == 0 or self.CurrentThick == 0 or self.WeldJointEffciency == 0 or (self.YieldStrengthDesignTemp == 0 and self.TensileStrengthDesignTemp == 0)):
                    return 6500;
                else:
                    a = self.Po_P1_Thin() * self.ncdf(- self.B1_Thin(age))
                    b = self.Po_P2_Thin() * self.ncdf(- self.B2_Thin(age))
                    c = self.Po_P3_Thin() * self.ncdf(- self.B3_Thin(age))
                    return (a + b + c) / (1.56 * pow(10, -4))
            except Exception as e:
                print(e)
                return 0

    def DF_THIN(self, age):
        Fwd = 1
        Fam = 1
        Fsm = 1
        if (self.HighlyEffectDeadleg):
            Fip = 3
        else:
            Fip = 1
        if (self.ContainsDeadlegs):
            Fdl = 3
        else:
            Fdl = 1
        print(self.EquipmentType)
        if self.EquipmentType == "Tank":
            if (self.ComponentIsWeld):
                Fwd = 1
            else:
                Fwd = 10
            if (self.TankMaintain653):
                Fam = 1
            else:
                Fam = 5

            if (self.AdjustmentSettle == "Recorded settlement exceeds API 653 criteria"):
                Fsm = 2
            elif (self.AdjustmentSettle == "Recorded settlement meets API 653 criteria"):
                Fsm = 1
            elif (self.AdjustmentSettle == "Settlement never evaluated"):
                Fsm = 1.5
            else:
                Fsm = 0
        if (
                                                                self.OnlineMonitoring == "Amine high velocity corrosion - Electrical resistance probes" or self.OnlineMonitoring == "Amine high velocity corrosion - Key process variable" or self.OnlineMonitoring == "Amine low velocity corrosion - Electrical resistance probes" or self.OnlineMonitoring == "HCL corrosion - Electrical resistance probes" or
                                                    self.OnlineMonitoring == "HCL corrosion - Key process variable" or self.OnlineMonitoring == "HF corrosion - Key process variable" or self.OnlineMonitoring == "High temperature H2S/H2 corrosion - Electrical resistance probes" or self.OnlineMonitoring == "High temperature Sulfidic / Naphthenic acid corrosion - Electrical resistance probes" or
                                    self.OnlineMonitoring == "High temperature Sulfidic / Naphthenic acid corrosion - Key process variable" or self.OnlineMonitoring == "Sour water high velocity corrosion - Key process variable" or self.OnlineMonitoring == "Sour water low velocity corrosion - Electrical resistance probes" or self.OnlineMonitoring == "Sulfuric acid (H2S/H2) corrosion high velocity - Electrical resistance probes" or
                    self.OnlineMonitoring == "Sulfuric acid (H2S/H2) corrosion high velocity - Key process parameters" or self.OnlineMonitoring == "Sulfuric acid (H2S/H2) corrosion low velocity - Electrical resistance probes"):
            Fom = 10
        elif (
                                    self.OnlineMonitoring == "Amine low velocity corrosion - Corrosion coupons" or self.OnlineMonitoring == "HCL corrosion - Corrosion coupons" or self.OnlineMonitoring == "High temperature Sulfidic / Naphthenic acid corrosion - Corrosion coupons" or self.OnlineMonitoring == "Sour water high velocity corrosion - Corrosion coupons" or self.OnlineMonitoring == "Sour water high velocity corrosion - Electrical resistance probes" or
                    self.OnlineMonitoring == "Sour water low velocity corrosion - Corrosion coupons" or self.OnlineMonitoring == "Sulfuric acid (H2S/H2) corrosion low velocity - Corrosion coupons"):
            Fom = 2
        elif (
                            self.OnlineMonitoring == "Amine low velocity corrosion - Key process variable" or self.OnlineMonitoring == "HCL corrosion - Key process variable & Electrical resistance probes" or self.OnlineMonitoring == "Sour water low velocity corrosion - Key process variable" or self.OnlineMonitoring == "Sulfuric acid (H2S/H2) corrosion high velocity - Key process parameters & electrical resistance probes" or self.OnlineMonitoring == "Sulfuric acid(H2S / H2) corrosion low velocity - Key process parameters"):
            Fom = 20
        else:
            Fom = 1
        a =  (self.DFB_THIN(age) * Fip * Fdl * Fwd * Fam * Fsm)/Fom
        return max(a,0.1)

    def GET_AGE(self):
        age = DAL_CAL.POSTGRESQL.GET_AGE_INSP(self.ComponentNumber,"Internal Thinning",self.CommissionDate, self.AssesmentDate)
        return age
###########
    def DF_THINNING_API(self, i):
        return self.DF_THIN(self.GET_AGE() + i)
    def DFB_THIN_API(self, i):
        return self.DFB_THIN_API(self.GET_AGE() + i)