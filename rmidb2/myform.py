from itertools import groupby
from turbogears.widgets import TableForm, CSSSource


class MultiColTableForm(TableForm):
    """TableForm allowing multiple fields per row.

    Fields having 'aside' as one of their css_classes appear on the same row.

    """

    template = """
    <form xmlns:py="http://purl.org/kid/ns#"
        name="${name}" action="${action}" method="${method}" class="tableform"
        py:attrs="form_attrs">
        <div py:for="field in hidden_fields"
            py:replace="field(value_for(field), **params_for(field))"/>
        <table border="0" cellspacing="0" cellpadding="6"
                py:for="row_no, row in rows(fields)" py:attrs="table_attrs">
            <tr {row_no % 2 and 'odd' or 'even'}"
                    valign="top"><td py:for="field in row">
                <label py:if="field.label" class="fieldlabel"
                    for="${field.field_id}" py:content="field.label"/>
                <span py:replace="field(value_for(field), **params_for(field))"/>
                <span py:if="error_for(field)" class="fielderror"
                    py:content="error_for(field)"/>
                <span py:if="field.help_text" class="fieldhelp"
                    py:content="field.help_text"/>
            </td></tr>
        </table>
        <div class="submit" py:content="submit(submit_text)"/>
    </form>
    """

    css = [CSSSource("""
    form.tableform {
        margin-bottom: 1ex;
    }
    form.tableform td {
        vertical-align: top;
    }
    form.tableform label.fieldlabel {
        display: block;
    }
    form.tableform div.submit {
        padding-top: 2ex;
    }
    """)]

    params = ['rows']

    @staticmethod
    def rows():
        """Return a function for creating the rows."""
        def gen_rows(fields):
            def row_no(field, no=[0]):
                if not 'aside' in field.css_classes:
                    no[0] += 1
                return no[0]
            return groupby(fields, row_no)
        return gen_rows
