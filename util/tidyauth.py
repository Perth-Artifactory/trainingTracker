# Functions here have are from tidyauth


def report_formatter(data: list, dtype: str) -> str:
    html = ""
    mrkdwn = ""

    for section in data:
        # Section title
        if "title" in section.keys():
            html += f'<h2>{section["title"]}</h2>\n'
            mrkdwn += f'## {section["title"]}\n'

        # Explainer paragraph
        if "explainer" in section.keys():
            html += f'<p>{section["explainer"]}</p>\n'
            mrkdwn += f'{section["explainer"]}\n'

        # Calculate table entry padding
        col_lengths = []
        for col in range(len(section["table"][0])):
            max_length = 0
            for line in section["table"]:
                try:
                    if len(str(line[col])) > max_length:
                        max_length = len(str(line[col]))
                except IndexError:
                    pass
            col_lengths.append(max_length)

        # Table head
        html += f'<table class="table">\n<thead>\n<tr>\n'
        for h in section["table"][0]:
            html += f'<th scope="col">{h}</th>\n'
        html += "</tr>\n</thead>\n<tbody>\n"
        mrkdwn += f'\n| {" | ".join([str(l).ljust(pad," ") for l,pad in zip(section["table"][0],col_lengths)])} |\n'
        mrkdwn += f'| {" | ".join([i*"-" for i in col_lengths])} |\n'

        # Table body

        for line in section["table"][1:]:
            hline = [str(l).replace("\n", "<br/>") for l, pad in zip(line, col_lengths)]
            mline = [
                str(l).replace("\n", ", ").ljust(pad, " ")
                for l, pad in zip(line, col_lengths)
            ]
            html += "<tr>\n"
            max_item_len = 0
            for item in hline:
                html += f"<td>{item}</td>\n"
                if len(item) > max_item_len:
                    max_item_len = len(item)
            html += "</tr>\n"
            mrkdwn += f'| {" | ".join(mline)} |\n'
        html += "</tbody>\n</table>\n"

        # Only add a page break if we have multiple sections
        if len(data) > 1:
            html += "<hr>\n"
            mrkdwn += "\n---\n"

    if dtype == "mrkdwn":
        return mrkdwn
    elif dtype == "html":
        try:
            with open("report_template.html", "r") as f:
                html_wrapper = f.read()
        except FileNotFoundError:
            with open("./scripts/report_template.html", "r") as f:
                html_wrapper = f.read()
        return html_wrapper.format(html)
    elif dtype == "html_embed":
        return html
    return ""
