import sqlite3

import PyPDF2
import os


def get_files(path):
    dir_list = os.scandir(path)
    final_list = []
    for entry in dir_list:
        if entry.is_dir():
            sub_list = get_files(os.path.join(path, entry.path))
            final_list += sub_list
        if entry.name.endswith('.pdf'):
            final_list.append(entry.path)
            print('doc: ', entry.path)

    return final_list


def get_date(text):
    x = text.find("Data Pregão") + 11
    return text[x:x+11].replace("\n", "")


def get_tax_liquidacao(text):
    x = text.find("Taxa de Liquidação") + 18
    y = text.find("Taxa de Registro")
    return text[x:y].replace("\n", "")


def get_emoluments(text):
    x = text.find("Emolumentos") + 11
    y = text.find("Total Bolsa")
    return text[x:y].replace("\n", "")


def get_first_line_with_value(text):
    for line in text.split('\n'):
        if len(line) > 0:
            return line


def get_double_check_emoluments(text):
    x = text.find("Total Bolsa") + 11
    y = text.find("Corretagem/Despesas")
    sub_str = text[x:y].replace("Total Bolsa", "")
    return get_first_line_with_value(sub_str)


def find_string(txt, str1):
    return txt.find(str1, txt.find(str1)+1)


def get_corretagem(text):
    x = find_string(text, "Corretagem")
    y = text.find("ISS (SÃO PAULO)")
    sub_str = text[x:y].replace("Corretagem/Despesas", "").replace("Corretagem", "").replace("\n", "")
    return sub_str


def get_double_check_corretagem(text):
    x = text.find("Total Corretagem/Despesas") + 25
    y = text.find("Líquido para")
    sub_str = text[x:y].replace("Total Corretagem/Despesas", "")
    sub_str = get_first_line_with_value(sub_str)
    return sub_str


def get_all_corretagens(text):
    result_list = []

    while not len(text) == 0:
        x = text.find("BOVESPA") + 8
        y = text.find("Resumo dos Negócios")

        sub_str = text[x:y]
        if len(sub_str) == 0:
            return

        while not sub_str[0].isalpha():
            sub_str = sub_str.replace("\n", "", 1)

        tipo_op = sub_str[0:1]
        sub_str = sub_str.replace(tipo_op, "", 1).replace("\n", "", 1).replace("VISTA", "", 1)
        sub_str = sub_str.replace("FRACIONARIO", "", 1)
        sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]
        stock = sub_str[0:sub_str.find(" ")]

        sub_str = sub_str.replace(stock, "", 1)
        sub_str = sub_str[1: len(sub_str)]
        while not sub_str[0].isnumeric():
            sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]

        qtd = sub_str[0: sub_str.find("\n")]
        sub_str = sub_str.replace(qtd, "", 1)
        sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]
        value = sub_str[0: sub_str.find("\n")]

        sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]
        total = sub_str[0: sub_str.find("\n")]

        sub_str = sub_str.replace(total, "", 1)
        sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]
        sub_str = sub_str[1:len(sub_str)]
        sub_str = sub_str[sub_str.find("\n") + 1: len(sub_str)]

        if sub_str.find("NuInvest Corretora") == 0:
            sub_str = ""
        if sub_str.find("Mercado\nMercado") == 0:
            sub_str = ""

        x = {
            f'tipo_op': f'{tipo_op}',
            'ticker': f'{stock}',
            'qtd': f'{qtd}',
            'value': f'{value}',
            'total': f'{total}'
        }
        text = sub_str
        # print(x)
        # print(text)
        result_list.append(x)

    return result_list
    # print(tipo_op, stock, qtd, value, total)


def save_on_db(tickers, date, tax_transaction, emolument, emolument_dc, corretagem, corretagem_dc):
    conn = sqlite3.connect('database.db')
    curs = conn.cursor()
    for i in range(0, len(tickers)):
        curs.execute(f'insert into operations '
                     '(date, tax_transaction, emolument, emolument_dc, corretagem, corretagem_dc, '
                     'ticker, operation, qtd, value, total) '
                     'values '
                     '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                     (date, tax_transaction, emolument, emolument_dc, corretagem, corretagem_dc,
                      tickers[i]['ticker'], tickers[i]['tipo_op'], tickers[i]['qtd'], tickers[i]['value'], tickers[i]['total'])
                     )
        conn.commit()


def read_page(page, is_first, is_last):
    text = page.extractText()
    result = get_all_corretagens(text)
    return result


def read_pdf(file_name):
    pdf_file = open(file_name, 'rb')
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)
    num_pages = pdf_reader.numPages

    page = pdf_reader.getPage(0)
    text = page.extractText()
    date = get_date(text)

    page = pdf_reader.getPage(pdf_reader.numPages - 1)
    text = page.extractText()
    tax_transaction = get_tax_liquidacao(text)
    emolument = get_emoluments(text)
    emolument_dc = get_double_check_emoluments(text)
    corretagem = get_corretagem(text)
    corretagem_dc = get_double_check_corretagem(text)

    for i in range(num_pages):
        page = pdf_reader.getPage(i)
        result = read_page(page, i == 0, i == num_pages - 1)
        if result is not None:
            #save_on_db(result, date, tax_transaction, emolument, emolument_dc, corretagem, corretagem_dc)
            print(result, date, tax_transaction, emolument, emolument_dc, corretagem, corretagem_dc)

    pdf_file.close()


def main(path):
    files = get_files(path=path)
    for i in range(len(files)):
       read_pdf(file_name=files[i])


if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(r"F:\Dev\Python\readNuInvestStatements\docs\tmp\tmp"))
    print('dir: ', dir_path)
    main(path=dir_path)
