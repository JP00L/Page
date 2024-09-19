from flask import Flask, render_template, request, jsonify
import pdfplumber,re,requests,json,difflib,math
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

def Extraccion(Certificado):
    item={}
    item['Certificado'] = Certificado.filename.replace(".pdf", "")
    def Buscar_Entro_Texto(RAY,Texto):
        pattern = re.escape(RAY[0]) + r'.*?([\w_ ]+?)' + re.escape(RAY[1])

        match = re.search(pattern, Texto)
        if match:
            nombre_completo = match.group(1).replace('_', '').strip()
            return nombre_completo
        else:
            return None
    def Buscar_Dentro_PDF(Tabla_Datos,Busqueda,Recuento=None):
        Validacion = None
        TD_RT=[]
        Temp_IT=0
        Index_Recinto=None
        for fila in Tabla_Datos:
            try:
                if type(Recuento) is list:
                    Cuenta = fila.index(Busqueda)
                    return Buscar_Entro_Texto(Recuento[1].split(","),fila[Cuenta+Recuento[0]])
                elif "," in str(Recuento):
                    for Dato in fila:
                        if Busqueda in Dato or Validacion == True:
                            if Busqueda == "Uso":
                                if Buscar_Entro_Texto(Recuento.split(","), Dato).upper() == "X":
                                    return "Residencial"
                                else:
                                    return "Comercial"
                            elif Busqueda == "CUENTA CON VACIO INTERNO":
                                if Validacion:
                                    if "X" in Dato:
                                        return Dato.replace("X", "").replace(" ", "")
                                else:
                                    Validacion = True
                                    break
                            elif Busqueda == "Corresponde Medidor":
                                if Buscar_Entro_Texto(Recuento.split(","), Dato).upper() == "X":
                                    return True
                                else:
                                    return False
                            else:
                                return Buscar_Entro_Texto(Recuento.split(","), Dato) 
                elif Recuento == "Censo":
                    RAY=["A","B","C","D","E","F","G","H","I","J"]
                    for Dato in fila:
                        if 'Área Inferior Existente\n(cm2)' in fila:
                            return TD_RT
                        if "Medidor Real" in fila:
                            Validacion = True
                            
                        if Validacion:
                            if Dato in RAY:
                                for i in RAY:
                                    if i in fila:
                                        indices = [t for t, r in enumerate(fila) if r == i]
                                        IND =indices[len(indices)-1]
                                        Index_Recinto=IND
                                        
                                try:
                                    if fila[Index_Recinto+2] == "9090":
                                        Temp_IT+= 1
                                        TD_RT.append({f'Censo':{"Recinto":fila[Index_Recinto],"Descripcion":fila[Index_Recinto+1],'Artefacto':fila[Index_Recinto+2],"Potencia":float("0.0" if "N" in fila[Index_Recinto+3] else fila[Index_Recinto+3])}})
                                        break
                                    elif fila[Index_Recinto] in RAY and float(fila[Index_Recinto+3]):
                                        Temp_IT+= 1
                                        TD_RT.append({f'Censo':{"Recinto":fila[Index_Recinto],"Descripcion":fila[Index_Recinto+1],'Artefacto':fila[Index_Recinto+2],"Potencia":float(fila[Index_Recinto+3])}})
                                        break
                                except:
                                    pass
                elif Recuento == "Recinto":
                    for Dato in fila:
                        if 'ANEXO 2 Resolución 9 0902 de 2013 QUE MODIFICÓ LA RESOLUCIÓN 41385 DE 2017' in fila:
                            return TD_RT
                        if 'Área Inferior Existente\n(cm2)' in fila:
                            Validacion = True
                            break
                            
                        if Validacion:
                            if fila[0] == "":
                                break
                            else:
                                Temp_IT+= 1
                                TD_RT.append({f'Recinto':{"Recinto":fila[0],"Valor Co":fila[2],"Sumatoria":float(fila[4])}})
                                break

                else:
                    Cuenta = fila.index(Busqueda)
                    if Recuento is None:
                        return fila
                    else:
                        if Busqueda == 'Medidor Factura' or  Busqueda == 'Medidor Real':
                            return Buscar_Entro_Texto(Recuento.split(","), fila[Cuenta + Recuento])
                        else:
                            return fila[Cuenta + Recuento]
            except:
                pass
    def Extraccion_Tabla(Certificado):
        TD = []
        with pdfplumber.open(Certificado) as pdf:
            for i, pagina in enumerate(pdf.pages):
                tablas = pagina.extract_tables()        
                for tabla in tablas:
                    if i != 1:
                        for fila in tabla:
                            fila_sin_none = [elemento for elemento in fila if elemento is not None]
                            if fila_sin_none:
                                TD.append(fila_sin_none)
                break
        return TD

    RAY={
        "Vanti":{
            'DIA':1,
            'MES':1,
            'AÑO':1,
            'Uso':'Residencial,Comercial',
            'Hora Inicio Insp':1,
            'Hora Final Insp':1,
            'Nombre completo Cliente':1,
            'No. Identificación cliente':1,
            'Teléfono':1,
            'Dirección':1,
            'Cuenta Número':1,
            'Barrio':1,
            'Ciudad/Municipio':1,
            'Departamento':1,
            'CUENTA CON VACIO INTERNO':",",
            'Corresponde Medidor':'SI,NO',
            'Medidor Factura':[1,'S/N,Lectura'],
            'Medidor Factura_Lectura':[1,'Lectura,m3'],
            'Medidor Real':[1,'S/N,Lectura'],
            'Medidor Real_Lectura':[1,'Lectura,m3'],
            'Censo':'Censo',
            'Recinto':'Recinto',
            'Nombre Completo':'Nombre Completo,\nCedula',
            'Cedula':'\nCedula,Vinculo',
            'Vinculo':'Vinculo,\nFirma'
        }
    }

    TD = Extraccion_Tabla(Certificado)

    for Plataforma in RAY:
        for Tipo in RAY[Plataforma]:
            if "_" in Tipo:
                item[Tipo]=Buscar_Dentro_PDF(TD,Tipo.split("_")[0],RAY[Plataforma][Tipo])
            else:
                item[Tipo]=Buscar_Dentro_PDF(TD,Tipo,RAY[Plataforma][Tipo]) 
    return item

def Cargue_Vanti(Cokies,ID_Base,DB,Certificado,Excepti=None):
    session = requests.Session()

    headers = {
    'Cookie': f'LOGIN_USERNAME_COOKIE=95000048%40grupovanti.co; ORA_WWV_APP_105={Cokies}; ORA_WWV_RAC_INSTANCE=9'
    }
    session.headers.update(headers)

    def Validacion_Datos_PDf(DataBase,DataBaseVanti=None,Excepti=None):
        Fecha_Base = f"{DataBase['DIA']}-{DataBase['MES']}-{DataBase['AÑO']} "
        Fecha_Incial =datetime.strptime(f"{Fecha_Base}{DataBase['Hora Inicio Insp']}", "%d-%m-%Y %H:%M").strftime("%d-%b-%Y %I:%M%p") 
        Fecha_Final = datetime.strptime(f"{Fecha_Base}{DataBase['Hora Final Insp']}", "%d-%m-%Y %H:%M").strftime("%d-%b-%Y %I:%M%p")    

        fecha1 = datetime.strptime(Fecha_Incial, "%d-%b-%Y %I:%M%p")
        fecha2 = datetime.strptime(Fecha_Final, "%d-%b-%Y %I:%M%p")
        if fecha1 >= fecha2:
            return "Error-Fecha Incial No Puede Ser Mayor o Igual A La Final"
        if DataBase['Corresponde Medidor']:
            if DataBase['Medidor Factura'] == DataBase['Medidor Real'] or Excepti is True:
                pass
            else:
                return "Error-Medidor Factura O Medidor Real No Coinciden"
            
        if DataBase['Medidor Factura_Lectura'] == DataBase['Medidor Real_Lectura'] or Excepti is True:
            pass
        else:
            return "Error-Lecturas Diferentes"       
            
        SumaRecintos_A=0
        SumaRecintos_B=0
        SumaRecintos_C=0
        SumaRecintos_D=0
        SumaRecintos_E=0
        SumaRecintos_F=0
        SumaRecintos_G=0
        SumaRecintos_H=0
        for i in DataBase['Censo']:
            if i['Censo']['Recinto'] == "A":
                SumaRecintos_A+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "B":
                SumaRecintos_B+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "C":
                SumaRecintos_C+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "D":
                SumaRecintos_D+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "E":
                SumaRecintos_E+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "F":
                SumaRecintos_F+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "G":
                SumaRecintos_G+= i['Censo']['Potencia']
            if i['Censo']['Recinto'] == "H":
                SumaRecintos_H+= i['Censo']['Potencia']
                
        for i in DataBase['Recinto']:
            if i['Recinto']['Recinto'] == "A":
                if not math.isclose(SumaRecintos_A, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado A"
            if i['Recinto']['Recinto'] == "B":
                if not math.isclose(SumaRecintos_B, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado B"
            if i['Recinto']['Recinto'] == "C":
                if not math.isclose(SumaRecintos_C, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado C"
            if i['Recinto']['Recinto'] == "D":
                if not math.isclose(SumaRecintos_D, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado D"
            if i['Recinto']['Recinto'] == "E":
                if not math.isclose(SumaRecintos_E, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado E"
            if i['Recinto']['Recinto'] == "F":
                if not math.isclose(SumaRecintos_F, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado F"
            if i['Recinto']['Recinto'] == "G":
                if not math.isclose(SumaRecintos_G, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado G"
            if i['Recinto']['Recinto'] == "H":
                if not math.isclose(SumaRecintos_H, i['Recinto']['Sumatoria']): return "Error-Sumatoria De Recintos Errado H"

        if DataBaseVanti is not None:
            MedidorVanti=DataBaseVanti['Medidor']
            if Excepti is True:
                pass
            else:           
                if "-" in MedidorVanti:
                    if int(MedidorVanti.split("-")[1]) != int(DataBase['Medidor Real']):return "Error-Medidor Vanti Y Medidor"
                else:
                    if int(MedidorVanti) != int(DataBase['Medidor Real']):return "Error-Medidor Incompleto Respecto Al De Vanti"
                
            
            Ciudad_PDF =DataBase['Ciudad/Municipio']
            Ciudad_PDF = Ciudad_PDF.replace("á","a").replace("é","e").replace("ó","o").replace("ú","u").replace("í","i").upper()
            Ciudad_Vanti =DataBaseVanti['Municipio']
            Ciudad_Vanti = Ciudad_Vanti.replace("á","a").replace("é","e").replace("ó","o").replace("ú","u").replace("í","i").upper()

            if Ciudad_Vanti in Ciudad_PDF:
                pass
            else:
                return "Error-Municipio Errado"
            
            List_Uso_Vanti={'1':"Residencial",
                    '2':'Comercial',
                    '3':'Comercial'
            }
            
            Uso_PDF=DataBase['Uso']
            Uso_Vanti=List_Uso_Vanti[DataBaseVanti['Uso']]
            if Uso_PDF == Uso_Vanti or Excepti is True:
                return {'Url':DataBaseVanti['Url'],'Fecha_Incial':Fecha_Incial.replace("Jan","Ene").replace("Apr","Abr").replace("Aug","Ago").replace("Dec","Dic"),'Fecha_Final':Fecha_Final.replace("Jan","Ene").replace("Apr","Abr").replace("Aug","Ago").replace("Dec","Dic")}
            else:
                return f"Error-Uso Errado Registrado {Uso_Vanti}"

    def Identificar_Cliente(Solicitud_Base,Cuenta):
        if len(Cuenta) >8:
            return f"La Cuenta {Cuenta} tiene {len(Cuenta)} Caracteres No Es Posible Cargarla"
        else:
            url = f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:5:{Solicitud_Base}:::RP,5,6,7,8,9,10,11::"
            Html_1=session.request("GET", url)

            try:
                soup = BeautifulSoup(Html_1.text, 'html.parser')
                p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
                P5_SOLICITUD_ID = soup.find("input", {"data-for": "P5_SOLICITUD_ID"})["value"]
                protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
                Salt = soup.find("input", {"id": "pSalt"})["value"]
            except:
                return "Error-Al Procesar Datos Vanti"
            data_to_submit  = {
                "pageItems": {
                    "itemsToSubmit": [
                        {"n": "P5_CUENTA_CONTRATO", "v": Cuenta},
                        {"n": "P5_PROCESO", "v": "3"},
                        {"n": "P5_SOLICITUD_ID", "v": "", "ck": P5_SOLICITUD_ID}
                    ],
                    "protected": protected,
                    "rowVersion": "",
                    "formRegionChecksums": []
                },
                "salt": Salt
            }
            P_JSON_string = json.dumps(data_to_submit)
            url = f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:5:{Solicitud_Base}"
            payload = {'p_flow_id': '105',
            'p_flow_step_id': '5',
            'p_instance': Solicitud_Base,
            'p_debug': '',
            'p_request': 'NEXT',
            'p_reload_on_submit': 'S',
            'p_page_submission_id': p_page_submission_id,
            'p_json':P_JSON_string}
            response = session.request("POST", url, data=payload)

            try:
                response = response.json()
                RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
                return RT
            except:
                return "Error-No Retorna Una Url Valida"
    def Datos_Cliente(Solicitud_Base,Datos):
        Html_2 =session.get(Datos['Url'])
        try:
            soup = BeautifulSoup(Html_2.text, 'html.parser')
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            P6_CUENTA_CONTRATO = soup.find("input", {"name": "P6_CUENTA_CONTRATO"})["value"]
            P6_CUENTA_CONTRATO_ck= soup.find("input", {"data-for": "P6_CUENTA_CONTRATO"})["value"]
            P6_NOMBRE = soup.find("input", {"name": "P6_NOMBRE"})["value"]
            P6_NOMBRE_ck= soup.find("input", {"data-for": "P6_NOMBRE"})["value"]
            P6_USO = soup.find("input", {"name": "P6_USO"})["value"]
            P6_USO_ck= soup.find("input", {"data-for": "P6_USO"})["value"]
            P6_SOLICITUD_ID = soup.find("input", {"name": "P6_SOLICITUD_ID"})["value"]
            P6_SOLICITUD_ID_ck= soup.find("input", {"data-for": "P6_SOLICITUD_ID"})["value"]
            P6_SEGUIR_FLUJO = soup.find("input", {"name": "P6_SEGUIR_FLUJO"})["value"]
            P6_SEGUIR_FLUJO_ck= soup.find("input", {"data-for": "P6_SEGUIR_FLUJO"})["value"]
            MEDIDOR= soup.find("input", {"id": "P6_MEDIDOR"})["value"]
            P6_MUNICIPIO= soup.find("input", {"id": "P6_MUNICIPIO"})["value"]
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
        except:
            return "Error-Al Procesar Datos Vanti"
        data_to_submit={
        "pageItems": {
            "itemsToSubmit": [
            { "n": "P6_CUENTA_CONTRATO", "v": P6_CUENTA_CONTRATO, "ck": P6_CUENTA_CONTRATO_ck },
            { "n": "P6_NOMBRE", "v": P6_NOMBRE, "ck": P6_NOMBRE_ck },
            { "n": "P6_USO", "v": P6_USO, "ck": P6_USO_ck },
            { "n": "P6_SOLICITUD_ID", "v": P6_SOLICITUD_ID, "ck": P6_SOLICITUD_ID_ck },
            { "n": "P6_SEGUIR_FLUJO", "v": P6_SEGUIR_FLUJO, "ck": P6_SEGUIR_FLUJO_ck }
            ],
            "protected": protected,
            "rowVersion": "",
            "formRegionChecksums": []
        },
        "salt": Salt
        }
        P_JSON_string = json.dumps(data_to_submit)
        url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:6:{Solicitud_Base}"
        payload={
        "p_flow_id": "105",
        "p_flow_step_id": "6",
        "p_instance": Solicitud_Base,
        "p_debug": "",
        "p_request": "NEXT",
        "p_reload_on_submit": "S",
        "p_page_submission_id": p_page_submission_id,
        'p_json':P_JSON_string
        }
        response = session.request("POST", url, data=payload)

        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}',
                'Medidor':MEDIDOR,
                'Municipio':P6_MUNICIPIO,
                'Uso':P6_USO
                }
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Datos_básicos(Solicitud_Base,Datos,Datos_V):
        Html_3 =session.get(Datos_V['Url'])
        try:
            soup = BeautifulSoup(Html_3.text, 'html.parser')
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            P7_FECHA_MAXIMA= soup.find("input", {"name": "P7_FECHA_MAXIMA"})["value"]
            P7_FECHA_MAXIMA_ck= soup.find("input", {"data-for": "P7_FECHA_MAXIMA"})["value"]
            P7_FECHA_INSPECCION= soup.find("input", {"name": "P7_FECHA_INSPECCION"})["value"]
            P7_FECHA_INSPECCION_ck= soup.find("input", {"data-for": "P7_FECHA_INSPECCION"})["value"]
            P7_PROCESO= soup.find("input", {"name": "P7_PROCESO"})["value"]
            P7_PROCESO_ck= soup.find("input", {"data-for": "P7_PROCESO"})["value"]
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
        except:
            return "Error-Al Procesar Datos Vanti"
        P7_HORA_INICIO = Datos_V['Fecha_Incial']
        P7_HORA_FIN= Datos_V['Fecha_Final']
        
        P7_VACIO = "" if Datos['CUENTA CON VACIO INTERNO'].upper() == "NO" else "S"
        P7_NUMERO_CERTIFICADO =Datos['Certificado'].translate(str.maketrans('', '', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        P7_LECTURA=Datos['Medidor Real_Lectura']
        P7_OBSERVACIONES= "" if Datos['Corresponde Medidor'] == True else f"Medidor Real:{Datos['Medidor Real']} / Medidor Factura:{Datos['Medidor Factura']}"
            
        data_to_submit={
            "pageItems": {
            "itemsToSubmit": [
                { "n": "P7_FECHA_MAXIMA", "v": P7_FECHA_MAXIMA, "ck": P7_FECHA_MAXIMA_ck },
                { "n": "P7_RESULTADO_INSPECCION", "v": "Correcto" },
                { "n": "P7_FECHA_INSPECCION", "v": P7_FECHA_INSPECCION, "ck": P7_FECHA_INSPECCION_ck },
                { "n": "P7_HORA_INICIO", "v": P7_HORA_INICIO },
                { "n": "P7_HORA_FIN", "v": P7_HORA_FIN },
                { "n": "P7_INSPECTOR", "v": "" },
                { "n": "P7_VACIO_INTERNO_SN", "v": [P7_VACIO] },
                { "n": "P7_APLICA_EXCEPCION_NORMA_SN", "v": [] },
                { "n": "P7_PRESION_DINAMICA", "v": "" },
                { "n": "P7_PRESION_ESTATICA", "v": "" },
                { "n": "P7_MEDIDA", "v": "" },
                { "n": "P7_NUMERO_CERTIFICADO", "v": P7_NUMERO_CERTIFICADO },
                { "n": "P7_LECTURA", "v": P7_LECTURA },
                { "n": "P7_RADICADO_SUSPENSION", "v": "" },
                { "n": "P7_DEFECTOS", "v": "" },
                { "n": "P7_OBSERVACIONES", "v": P7_OBSERVACIONES },
                { "n": "P7_PROCESO", "v": P7_PROCESO, "ck": P7_PROCESO_ck}
            ],
            "protected": protected,
            "rowVersion": "",
            "formRegionChecksums": []
            },
            "salt": Salt
        }
        P_JSON_string = json.dumps(data_to_submit)
        url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:7:{Solicitud_Base}"
        payload={
            "p_flow_id": "105",
            "p_flow_step_id": "7",
            "p_instance": Solicitud_Base,
            "p_debug": "",
            "p_request": "NEXT",
            "p_reload_on_submit": "S",
            "p_page_submission_id": p_page_submission_id,
            'p_json':P_JSON_string
        }
        response = session.request("POST", url, data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Carga_instalada(Solicitud_Base,Datos):
        def Eliminar_Todo_Artefacto(Solicitud_Base):
            while True:
                try:
                    URL=f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:8:{Solicitud_Base}:::RP::'
                    Html_14= session.get(URL)
                    soup = BeautifulSoup(Html_14.text, 'html.parser')
                    Censos=soup.find("a", {"class": "t-Button t-Button--warning"})["href"]
                    Censos = Censos.replace("javascript:apex.navigation.dialog(","").replace("'","").replace("\\u0026","&").split(",{title:")[0]
                    Url=f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{Censos}'
                    response= session.get(Url)

                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
                        protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
                        Salt = soup.find("input", {"id": "pSalt"})["value"]
                        P16_SEQ = soup.find("input", {"name": "P16_SEQ"})["value"]
                        P16_SEQ_ck = soup.find("input", {"data-for": "P16_SEQ"})["value"]
                        select_element_0 = soup.find('select', {'name': 'P16_DESCRIPCION'})
                        P16_DESCRIPCION = select_element_0.find("option", {"selected": "selected"})["value"]
                        P16_KW = soup.find("input", {"name": "P16_KW"})["value"]
                        select_element_0 = soup.find('select', {'name': 'P16_RECINTO'})
                        P16_RECINTO = select_element_0.find("option", {"selected": "selected"})["value"]
                        P16_ESTADO = soup.find("input", {"name": "P16_ESTADO", "checked": "checked"})["value"]
                    except:
                        return "Error-Al Procesar Datos Vanti"
                    data_to_submit={
                    "pageItems": {
                        "itemsToSubmit": [
                        {"n": "P16_SEQ", "v": P16_SEQ ,"ck": P16_SEQ_ck},
                        {"n": "P16_DESCRIPCION", "v": P16_DESCRIPCION},
                        {"n": "P16_KW", "v": P16_KW},
                        {"n": "P16_RECINTO", "v": P16_RECINTO},
                        {"n": "P16_ESTADO", "v":P16_ESTADO}
                        ],
                        "protected": protected,
                        "rowVersion": "",
                        "formRegionChecksums": []
                    },
                    "salt": Salt
                    }
                    P_JSON_string = json.dumps(data_to_submit)
                    url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:16:{Solicitud_Base}"
                    payload={
                    "p_flow_id": "105",
                    "p_flow_step_id": "16",
                    "p_instance": Solicitud_Base,
                    "p_debug": "",
                    "p_request": "Eliminar",
                    "p_reload_on_submit": "S",
                    "p_page_submission_id": p_page_submission_id,
                    'p_json':P_JSON_string
                    }
                    response = session.request("POST", url, data=payload)
                except:
                    break
        def Agregar_Artefactos(Solicitud_Base,Datos):
            with open("static/Censos.json", 'r',encoding="utf-8") as f:
                contenido = f.read()
            Data = json.loads(contenido)
            
            Html_4 =session.get(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:8:{Solicitud_Base}:::::')
            try:
                soup = BeautifulSoup(Html_4.text, 'html.parser')
                p_dialog_cs= soup.find("button", {"class": "t-Button js-ignoreChange"})["onclick"]
                p_dialog_cs = p_dialog_cs.replace("javascript:apex.navigation.dialog(","").replace("'","").replace("\\u0026","&").split(",{title:")[0]
            except:
                return "Error Al Extraer Los Datos"


            url_4=f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{p_dialog_cs}'
            Html_5 =session.get(url_4)
            
            try:
                soup = BeautifulSoup(Html_5.text, 'html.parser')
                protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
                Salt = soup.find("input", {"id": "pSalt"})["value"]
                p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            except:
                return "Error-Al Extraer Los Datos"
            try:
                P15_DESCRIPCION_0=Data["Censos_Vanti_ID"][0][Datos['Artefacto']]
            except:
                return "Error-Al Buscar Censo En Vanti"
            P15_RECINTO= Data["Recintos_Censos_ID"][0][Datos['Recinto']]
            
            
            if Datos['Artefacto'] == "9090":
                P15_ESTADO = Data["Estado_Censos_ID"][0]["Previsto"]
                P15_KW = "0,0"
            else:
                P15_ESTADO = Data["Estado_Censos_ID"][0]["Instalado"]
                P15_KW = str(Datos['Potencia']).replace(".",",")
            
            
            data_to_submit={
            "pageItems": {
                "itemsToSubmit": [
                { "n": "P15_DESCRIPCION", "v":P15_DESCRIPCION_0  },
                { "n": "P15_KW", "v": P15_KW},
                { "n": "P15_RECINTO", "v": P15_RECINTO },
                { "n": "P15_ESTADO", "v": P15_ESTADO }
                ],
                "protected": protected,
                "rowVersion": "",
                "formRegionChecksums": []
            },
            "salt": Salt
            }

            P_JSON_string = json.dumps(data_to_submit)
            payload={
            "p_flow_id": "105",
            "p_flow_step_id": "15",
            "p_instance": Solicitud_Base,
            "p_debug": "",
            "p_request": "Adicionar",
            "p_reload_on_submit": "S",
            "p_page_submission_id": p_page_submission_id,
            'p_json':P_JSON_string
            }
            url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:15:{Solicitud_Base}"
            response = session.request("POST", url, data=payload)
            return response
        Eliminar_Todo_Artefacto(Solicitud_Base)
        for Data in Datos['Censo']:
            if "Error" in Agregar_Artefactos(Solicitud_Base,Data['Censo']):
                return  "Error-Al Agregar Censo"
            
        url_5=f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:8:{Solicitud_Base}:::RP::'
        Html_6 = session.get(url_5)
        try:
            soup = BeautifulSoup(Html_6.text, 'html.parser')
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            P8_INSPECCION_ID= soup.find("input", {"name": "P8_INSPECCION_ID"})["value"]
            P8_INSPECCION_ID_ck= soup.find("input", {"data-for": "P8_INSPECCION_ID"})["value"]
            P8_RESULTADO= soup.find("input", {"name": "P8_RESULTADO"})["value"]
            P8_RESULTADO_ck= soup.find("input", {"data-for": "P8_RESULTADO"})["value"]
            P8_INSPECTOR= soup.find("input", {"name": "P8_INSPECTOR"})["value"]
            P8_INSPECTOR_ck= soup.find("input", {"data-for": "P8_INSPECTOR"})["value"]
        except:
            return "Error-Al Procesar Datos Vanti"

        data_to_submit={
        "pageItems": {
            "itemsToSubmit": [
            { "n": "P8_INSPECCION_ID", "v": P8_INSPECCION_ID, "ck": P8_INSPECCION_ID_ck },
            { "n": "P8_RESULTADO", "v": P8_RESULTADO, "ck": P8_RESULTADO_ck },
            { "n": "P8_INSPECTOR", "v": P8_INSPECTOR, "ck": P8_INSPECTOR_ck }
            ],
            "protected": protected,
            "rowVersion": "",
            "formRegionChecksums": []
        },
        "salt": Salt
        }
        P_JSON_string = json.dumps(data_to_submit)
        payload={
        "p_flow_id": "105",
        "p_flow_step_id": "8",
        "p_instance": Solicitud_Base,
        "p_debug":"",
        "p_request": "NEXT",
        "p_reload_on_submit": "S",
        "p_page_submission_id": p_page_submission_id,
        'p_json':P_JSON_string
        }
    
        url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:8:{Solicitud_Base}"
        response = session.request("POST", url, data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Recintos(Solicitud_Base,Datos):
        Recintos_De_Censos={}
        Recintos={}

        for i in Datos['Censo']:
            if i['Censo']['Artefacto'] == "9090":
                if i['Censo']['Recinto'] in Recintos_De_Censos.keys():
                    pass
                else:
                    Recintos_De_Censos[i['Censo']['Recinto']] = None    
            else:
                Recintos_De_Censos[i['Censo']['Recinto']] = True

        for i in Datos['Recinto']:
            Recintos[i['Recinto']['Recinto']] = True


        diferencias_1 = Recintos.keys() - Recintos_De_Censos.keys()
        diferencias_2 = Recintos_De_Censos.keys() - Recintos.keys()
        if diferencias_1:
            # print("Error-No Coinciden Recintos Registrados En La Ventalcion, Con Los Registrados En Censo")
            return "Error-No Coinciden Recintos Registrados En La Ventalcion, Con Los Registrados En Censo"
        if diferencias_2:
            # print("Error-No Coinciden Recintos Registrados En Censo, Con Los Registrados En La Ventalcion")
            return "Error-No Coinciden Recintos Relacionados En El Censo Con Los Registrados En La Ventalcion"

        data_to_submit={}
        Html_4 =session.get(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:12:{Solicitud_Base}:CARGA_INSTALADA::::')

        try:
            soup = BeautifulSoup(Html_4.text, 'html.parser')
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            
            Item={'itemsToSubmit':[],'protected':'','rowVersion':'','formRegionChecksums':[]}
            It =1
            for i in Recintos_De_Censos:
                if Recintos_De_Censos[i]:
                    for o in Datos['Recinto']:
                        if o['Recinto']['Recinto'] == i:                       
                            Item['itemsToSubmit'].append({ "n": f"P12_RECINTO_0{It}", "v": soup.find("input", {"name": f"P12_RECINTO_0{It}"})["value"] , "ck": soup.find("input", {"data-for": f"P12_RECINTO_0{It}"})["value"] })
                        
                            Item['itemsToSubmit'].append({ "n": f"P12_ID_RECINTO_0{It}", "v": soup.find("input", {"name": f"P12_ID_RECINTO_0{It}"})["value"], "ck": soup.find("input", {"data-for": f"P12_ID_RECINTO_0{It}"})["value"] })
                            
                            Item['itemsToSubmit'].append({ "n": f"P12_KW_0{It}", "v": soup.find("input", {"name": f"P12_KW_0{It}"})["value"], "ck": soup.find("input", {"data-for": f"P12_KW_0{It}"})["value"] })
                            
                            #Toca Definir El Tipo De Recinto
                            Item['itemsToSubmit'].append({ "n": f"P12_TIPO_0{It}", "v": "3" })
                            
                            
                            Item['itemsToSubmit'].append({ "n": f"P12_VOLUMEN_CO_0{It}", "v": o['Recinto']['Valor Co'] })
                            It+= 1
                            break
            
            if not Item['itemsToSubmit']:
                pass
            else:    
                Item['protected'] = protected
                data_to_submit['pageItems'] = Item
    
            data_to_submit['salt'] = Salt
            
        except:
            return "Error-Al Procesar Datos Vanti"
        P_JSON_string = json.dumps(data_to_submit)
        payload={
        'p_flow_id':'105',
        'p_flow_step_id':'12',
        'p_instance':Solicitud_Base,
        'p_debug':'',
        'p_request':'NEXT',
        'p_reload_on_submit':'S',
        'p_page_submission_id':p_page_submission_id,
        'p_json':P_JSON_string
        }
        url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:12:{Solicitud_Base}"
        response = session.request("POST", url, data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Datos_Atendió(Solicitud_Base,Datos):
        try:
            Html_10 = session.get(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:9:{Solicitud_Base}')
            soup = BeautifulSoup(Html_10.text, 'html.parser')
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
        except:
            return "Error-Al Procesar Datos Vanti"
        def comparar_textos(texto1, texto2, umbral=0.8):
            similitud = difflib.SequenceMatcher(None, texto1, texto2).ratio()
            if similitud >= umbral:
                return True
            else:
                return False
            
        Vinculo= {
                "ADMINISTRADOR":"7",
                "ARRENDATARIO":"2",
                "EMPLEADO":"4",
                "ENCARGADO":"5",
                "FAMILIAR":"3",
                "MANTENIMIENTO":"8",
                "PROPIETARIO":"1",
                "VECINO":"6"        
            }
        Validacion_Vinculo=None
        for i in Vinculo.keys():
            coincide = comparar_textos(i, Datos['Vinculo'].upper())
            if coincide:
                Validacion_Vinculo = Vinculo[i]
        if Validacion_Vinculo is None: Validacion_Vinculo =Vinculo['ENCARGADO']
        
        P9_VINCULO=Validacion_Vinculo
        data_to_submit={
            "pageItems": {
            "itemsToSubmit": [
                { "n": "P9_NOMBRE", "v": Datos['Nombre Completo'].upper() },
                { "n": "P9_NRO_IDENTIFICACION", "v": Datos['Cedula'] },
                { "n": "P9_VINCULO", "v":P9_VINCULO },
                { "n": "P9_DIRECCION", "v": "" },
                { "n": "P9_TELEFONO", "v": "" }
            ],
            "protected": protected,
            "rowVersion": "",
            "formRegionChecksums": []
            },
            "salt": Salt
        }
        P_JSON_string = json.dumps(data_to_submit)
        payload={
            "p_flow_id":"105",
            "p_flow_step_id": "9",
            "p_instance": Solicitud_Base,
            "p_debug": "",
            "p_request": "NEXT",
            "p_reload_on_submit": "S",
            "p_page_submission_id": p_page_submission_id,
            'p_json':P_JSON_string
        }
        url=f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:9:{Solicitud_Base}"
        response = session.request("POST", url, data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Adjuntar_PDF(Solicitud_Base, Certificado):
        Html = session.get(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:10:{Solicitud_Base}')
        try:
            soup = BeautifulSoup(Html.text, 'html.parser')
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            P10_FILENAME = soup.find("input", {"data-for": "P10_FILENAME"})["value"]
            P10_ID = soup.find("input", {"data-for": "P10_ID"})["value"]
        except Exception as e:
            return f"Error-Al Procesar Datos Vanti: {e}"
        
        form_data = {
            "p_json": "{\"pageItems\":{\"itemsToSubmit\":[{\"n\":\"P10_FILE_BLOB\",\"v\":\"\",\"fileIndex\":1,\"fileCount\":1},{\"n\":\"P10_FILENAME\",\"v\":\"\",\"ck\":\""+P10_FILENAME+"\"},{\"n\":\"P10_ID\",\"v\":\"\",\"ck\":\""+P10_ID+"\"}],\"protected\":\""+protected+"\",\"rowVersion\":\"\",\"formRegionChecksums\":[]},\"salt\":\""+Salt+"\"}",
            "p_flow_id": "105",
            "p_flow_step_id": "10",
            "p_instance": Solicitud_Base,
            "p_debug": "",
            "p_request": "NEXT",
            "p_reload_on_submit": "S",
            "p_page_submission_id": p_page_submission_id
        }

        # Asegúrate de que el archivo PDF esté en modo binario antes de subirlo
        Certificado.seek(0)  # Asegurarse de que el puntero del archivo esté al principio
        file_to_upload = {
            'p_files': (Certificado.filename, Certificado.read(), 'application/pdf')  # Leemos el contenido en binario
        }

        url = f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:10:{Solicitud_Base}'
        response = session.post(url, files=file_to_upload, data=form_data)
        
        try:
            response_json = response.json()
            RT = {'Url': f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response_json["redirectURL"]}'}
            return RT
        except Exception as e:
            return f"Error-No Retorna Una Url Valida: {e}"
    def Finalizar(Solicitud_Base):
        try:
            Html_11 = session.get(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/f?p=105:11:{Solicitud_Base}')
            soup = BeautifulSoup(Html_11.text, 'html.parser')        
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]   
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            P11_ID_INSPECCION= soup.find("input", {"data-for": "P11_ID_INSPECCION"})["value"]
        except:
            return "Error-Al Procesar Datos Vanti"

        url = f"https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:10:{Solicitud_Base}"
        payload = {
        'p_flow_id': '105',
        'p_flow_step_id': '11',
        'p_instance': Solicitud_Base,
        'p_request': 'FINISH',
        'p_reload_on_submit': 'S',
        'p_page_submission_id': p_page_submission_id,
        'p_json': '{"pageItems":{"itemsToSubmit":[{"n":"P11_ID_INSPECCION","v":"","ck":"'+P11_ID_INSPECCION+'"}],"protected":"'+protected+'","rowVersion":"","formRegionChecksums":[]},"salt":"'+Salt+'"}'
        }

        response = session.post(url, data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"].split("&success_msg")[0]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
    def Notificar(Solicitud_Base,URL):
        Html = session.get(URL)
        try:
            soup = BeautifulSoup(Html.text, 'html.parser')
            protected = soup.find("input", {"id": "pPageItemsProtected"})["value"]
            Salt = soup.find("input", {"id": "pSalt"})["value"]
            p_page_submission_id = soup.find("input", {"name": "p_page_submission_id"})["value"]
            
            P17_NOMBRE_CLIENTE=  soup.find("input", {"id": "P17_NOMBRE_CLIENTE"})["value"]
            P17_NOMBRE_CLIENTE_ck=  soup.find("input", {"data-for": "P17_NOMBRE_CLIENTE"})["value"]
            
            P17_DIVISION= soup.find("input", {"id": "P17_DIVISION"})["value"]
            P17_DIVISION_ck= soup.find("input", {"data-for": "P17_DIVISION"})["value"]
            
            P17_MUNICIPIO= soup.find("input", {"id": "P17_MUNICIPIO"})["value"]
            P17_MUNICIPIO_ck=  soup.find("input", {"data-for": "P17_MUNICIPIO"})["value"]
            
            P17_DIRECCION= soup.find("input", {"id": "P17_DIRECCION"})["value"]
            P17_DIRECCION_ck= soup.find("input", {"data-for": "P17_DIRECCION"})["value"]
            
            P17_MEDIDOR= soup.find("input", {"id": "P17_MEDIDOR"})["value"]
            P17_MEDIDOR_ck= soup.find("input", {"data-for": "P17_MEDIDOR"})["value"]

            P17_CUENTA_CONTRATO= soup.find("input", {"id": "P17_CUENTA_CONTRATO"})["value"]
            P17_CUENTA_CONTRATO_ck= soup.find("input", {"data-for": "P17_CUENTA_CONTRATO"})["value"]

            P17_PROCESO= soup.find("input", {"id": "P17_PROCESO"})["value"]
            P17_PROCESO_ck= soup.find("input", {"data-for": "P17_PROCESO"})["value"]

            P17_ORGANISMO= soup.find("input", {"id": "P17_ORGANISMO"})["value"]
            P17_ORGANISMO_ck= soup.find("input", {"data-for": "P17_ORGANISMO"})["value"]

            P17_ID= soup.find("input", {"id": "P17_ID"})["value"]
            P17_ID_ck= soup.find("input", {"data-for": "P17_ID"})["value"]    
        except:
            return "Error-Al Procesar Datos Vanti"
        payload={
        'p_flow_id': '105',
        'p_flow_step_id': '17',
        'p_instance': Solicitud_Base,
        'p_debug': '',
        'p_request': 'enviar',
        'p_reload_on_submit': 'S',
        'p_page_submission_id': p_page_submission_id,
        'p_json': '{"pageItems":{"itemsToSubmit":[{"n":"P17_NOMBRE_CLIENTE","v":"'+P17_NOMBRE_CLIENTE+'","ck":"'+P17_NOMBRE_CLIENTE_ck+'"},{"n":"P17_DIVISION","v":"'+P17_DIVISION+'","ck":"'+P17_DIVISION_ck+'"},{"n":"P17_MUNICIPIO","v":"'+P17_MUNICIPIO+'","ck":"'+P17_MUNICIPIO_ck+'"},{"n":"P17_DIRECCION","v":"'+P17_DIRECCION+'","ck":"'+P17_DIRECCION_ck+'"},{"n":"P17_MEDIDOR","v":"'+P17_MEDIDOR+'","ck":"'+P17_MEDIDOR_ck+'"},{"n":"P17_CUENTA_CONTRATO","v":"'+P17_CUENTA_CONTRATO+'","ck":"'+P17_CUENTA_CONTRATO_ck+'"},{"n":"P17_PROCESO","v":"'+P17_PROCESO+'","ck":"'+P17_PROCESO_ck+'"},{"n":"P17_ORGANISMO","v":"'+P17_ORGANISMO+'","ck":"'+P17_ORGANISMO_ck+'"},{"n":"P17_ID","v":"'+P17_ID+'","ck":"'+P17_ID_ck+'"},{"n":"P17_RESULTADO_FIRMA_ESTAMPA","v":"Exitoso"}],"protected":"'+protected+'","rowVersion":"","formRegionChecksums":[]},"salt":"'+Salt+'"}'

        }

        response = session.post(f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/wwv_flow.accept?p_context=105:17:{Solicitud_Base}', data=payload)
        try:
            response = response.json()
            RT = {'Url':f'https://g9b63f06219a4ff-dbeweb1.adb.us-ashburn-1.oraclecloudapps.com/ords/{response["redirectURL"]}'}
            return RT
        except:
            return "Error-No Retorna Una Url Valida"
        
        



    Response =Identificar_Cliente(ID_Base,DB['Cuenta Número'])
    if "Error" in Response:
        # print(f'{Response}/[Identificar_Cliente]')
        return f'{Response}/[Identificar_Cliente]'
    else:
        Response =Datos_Cliente(ID_Base,Response)
        if "Error" in Response:
            # print(f'{Response}/[Datos_Cliente]')
            return f'{Response}/[Datos_Cliente]'
        else:
            Response = Validacion_Datos_PDf(DB,Response,Excepti)
            if "Error" in Response:
                # print(f'{Response}/[Validacion_Datos_PDf]')
                return f'{Response}/[Validacion_Datos_PDf]'
            else:
                Response = Datos_básicos(ID_Base,DB,Response)
                if "Error" in Response:
                    # print(f'{Response}/[Datos_básicos]')
                    return f'{Response}/[Datos_básicos]'
                else:
                    Response = Carga_instalada(ID_Base,DB)
                    if "Error" in Response:
                        # print(f'{Response}/[Carga_instalada]')
                        return f'{Response}/[Carga_instalada]'
                    else:
                        Response = Recintos(ID_Base,DB)
                        if "Error" in Response:
                            # print(f'{Response}/[Recintos]')
                            return f'{Response}/[Recintos]'
                        else:
                            Response = Datos_Atendió(ID_Base,DB)
                            if "Error" in Response:
                                # print(f'{Response}/[Datos_Atendió]')
                                return f'{Response}/[Datos_Atendió]'
                            else:
                                Response = Adjuntar_PDF(ID_Base,Certificado)
                                if "Error" in Response:
                                    # print(f'{Response}/[Adjuntar_PDF]')
                                    return f'{Response}/[Adjuntar_PDF]'
                                else:
                                    Response = Finalizar(ID_Base)
                                    if "Error" in Response:
                                        # print(f'{Response}/[Finalizar]')
                                        return f'{Response}/[Finalizar]'
                                    else:
                                        Response = Notificar(ID_Base,Response['Url'])
                                        if "Error" in Response:
                                            # print(f'{Response}/[Notificar]')
                                            return f'{Response}/[Notificar]'
                                        else:
                                            # print("Documento Notificado Correctamente")
                                            return "Documento Notificado Correctamente"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_files' not in request.files:
            return 'No files part', 400  # Devuelve un error 400 si no hay archivos

        files = request.files.getlist('pdf_files')  # Obtener la lista de archivos

        if not files or all(file.filename == '' for file in files):
            return 'No selected files', 400  # Devuelve un error 400 si no se seleccionaron archivos

        results = []
        for file in files:
            if file and file.filename.endswith('.pdf'):  # Verifica que sea un archivo PDF
                try:
                    extracted_data = Extraccion(file)  # Extraer datos del archivo
                    Cokies = request.form['Cokies'].strip()
                    ID_Base = request.form['ID_Base'].strip()
                    if request.form['processData']:
                        Estate= True
                    else:
                        Estate=None
                    
                    results.append(f'{file.filename}:{Cargue_Vanti(Cokies, ID_Base, extracted_data, file,Estate)}')  # Agrega el resultado a la lista
                except Exception as e:
                    results.append(f'{file.filename}:{str(e)}')

        return jsonify(results), 200  # Devuelve la lista de resultados en formato JSON
    
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)