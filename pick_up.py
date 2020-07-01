import pymysql
import socket


def isGTIN(str):
    # 校验14位GTIN编码
    # 校验方法在: GB 12904-2008
    format = '0123456789'

    if len(str) < 16:
        return False
    if str[:2] != '01':
        return False

    oddTotal = 0
    evenTotal = 0

    strGTIN = str[2:15][::-1]
    # 2-14位是GTIN编码，15位是校验码
    # 由于校验码是从右开始计数，所以逆序输出原字符串

    for i in range(0, len(strGTIN)):
        if not strGTIN[i] in format:
            return False
        if (i % 2 == 0):
            evenTotal = evenTotal + int(strGTIN[i])
        else:
            oddTotal = oddTotal + int(strGTIN[i])

    CRC = 10 - (evenTotal*3 + oddTotal) % 100 % 10
    # 计算校验码
    if CRC == 10:
        CRC = 0

    if CRC == int(str[15]):
        return True
    else:
        # print(CRC)
        return False


ip = socket.gethostbyname(socket.gethostname())
if ip == '127.0.0.1':
    host_ip = 'localhost'
else:
    host_ip = '47.95.32.68'

try:
    conn = pymysql.connect(
        host=host_ip,
        port=3306,
        user='ctmj',
        passwd='hDUIg7pb1Iy8',
        db='cold',
        charset='utf8',
    )
    cur = conn.cursor()
except:
    print('连接数据库异常.')
    exit(0)

sLoc = ''  # 库位编码
while sLoc != 'z':

    sLoc = input('库位:')
    sLoc = sLoc.strip()[:11]  # 截取前11位
    #sLoc = '79-10110203'
    if sLoc[3:].isdigit() and len(sLoc) == 11 and sLoc[2] == '-':  # 如果符合库位编码的格式
        sGS1 = '01'
        while sGS1 != '':
            quantity = 0  # 用户录入数量
            count = 0  # 库存数量
            sku_id = '未录入'  # 新SKU默认编码
            gtin = expire_date = batch = ''  # 初始化变量
            date_type = batch_type = box_no = ''  # 初始化变量

            sGS1 = input('扫描GS1:')
            #sGS1 = '01006431696999461719112710E0038825'
            #sGS1 = '+$$51405321205402TB'
            if sGS1 != '':
                if isGTIN(sGS1):
                    if len(sGS1) == 16:  # 如果GS1编码是16位，需要继续扫描第二部分GS1
                        sGS1_2 = input('扫描GS1_2: ')
                        if sGS1_2 != '':
                            sGS1 = sGS1 + sGS1_2
                    gtin = sGS1[:16]
                    print('GTIN:\t'+str(gtin))
                    # 输出效期
                    if sGS1[16:18] == '17':
                        #expire_date = sGS1[18:24]
                        expire_date = '20' + \
                            sGS1[18:20] + '-' + sGS1[20:22] + '-' + sGS1[22:24]
                        date_type = '失效日期'
                        print('效期:\t' + expire_date + '\t(' + date_type + ')')
                    elif sGS1[16:18] == '10':
                        #expire_date = sGS1[18:24]
                        expire_date = '20' + \
                            sGS1[18:20] + '-' + sGS1[20:22] + '-' + sGS1[22:24]
                        date_type = '生产日期'
                        print('效期:\t' + expire_date + '\t(' + date_type + ')')
                    else:
                        print('效期:\t--\t(未提供)')
                    # 输出批号/序列号
                    if sGS1[24:26] == '21':
                        batch = sGS1[26:]
                        print('批号:\t' + sGS1[26:])
                        batch_type = '序列号'
                    elif sGS1[24:26] == '10':
                        batch = sGS1[26:]
                        print('批号:\t' + sGS1[26:])
                        batch_type = '批号'
                    else:
                        print('批号:\t--\t(未提供)')

                    sql_1 = "select ref,box_id from mdt where gtin='"+gtin+"'"
                else:
                    print('CODE:\t'+str(sGS1)+'\t(非GS1编码)')
                    sql_1 = "select ref,box_id from mdt where gtin='"+sGS1+"'"

                cur.execute(sql_1)
                results_1 = cur.fetchone()

                if results_1:
                    print('货号:\t' + str(results_1[0]))
                    sku_id = str(results_1[0])
                    print('箱号:\t' + str(results_1[1]))
                    box_no = str(results_1[1])
                else:
                    sql_12 = "select ref,box_id from mdt_ref where batch='" + batch + "'"
                    cur.execute(sql_12)
                    results_12 = cur.fetchone()
                    if results_12:
                        print('货号:\t' + str(results_12[0])+"\t(?)")
                        sku_id = str(results_12[0])
                        print('箱号:\t' + str(results_12[1]))
                        box_no = str(results_12[1])
                    else:
                        print('货号:\t--\t(未找到)')
                        if isGTIN(sGS1):
                            sql_11 = "insert into mdt(gtin,ref,code_type,update_time) values('" + \
                                sGS1[:16]+"','未录入','GS1',now())"
                        else:
                            sql_11 = "insert into mdt(gtin,ref,code_type,update_time) values('" + \
                                sGS1+"','未录入','非GS1',now())"
                        cur.execute(sql_11)

                sql_2 = "select sum(quantity) from mdt_location  where gs1='" + \
                    sGS1 + "' and location='" + sLoc + "'"
                cur.execute(sql_2)
                results = cur.fetchone()

                if results:
                    if str(results[0]) == 'None':
                        print('数量:\t0')
                        count = '0'
                    else:
                        print('数量:\t' + str(results[0]))
                        count = str(results[0])
                else:
                    print('数量:\t0')

                quantity = input('上架数量[0]: ')
                if quantity != '' and quantity.isdigit():
                    if int(quantity) > 0 and int(quantity) < 32768:
                        sql_3 = ''
                        if int(count) > 0:
                            number = int(count) + int(quantity)
                            sql_3 = "update mdt_location set box_id='" + box_no + "',quantity=" + str(number) + \
                                ",ref='"+sku_id+"',update_time=now() where gs1='"+sGS1 + \
                                "' and location='"+sLoc+"'"
                        elif count == '0':
                            sql_3 = "insert into mdt_location (location,box_id,quantity,gs1,gtin,ref,expire_date,batch,date_type,batch_type,update_time)values('"+sLoc + \
                                "','"+box_no+"'," + quantity+",'"+sGS1+"','"+gtin+"','"+sku_id+"','" + \
                                    expire_date+"','"+batch.upper()+"','"+date_type+"','"+batch_type+"',now())"
                        cur.execute(sql_3)


cur.close()
# conn.commit()
conn.close()
