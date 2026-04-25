"""Build the daily HTML digest of new opportunities."""
from datetime import datetime


def build_digest_html(opportunities: list[dict]) -> str:
    rows = ""
    for o in opportunities:
        rows += f"""
        <tr>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('title','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('role','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('stipend','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('deadline','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('location','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>
                <a href='{o.get("apply_link","#")}'>Apply →</a>
            </td>
        </tr>"""

    return f"""
    <html><body style='font-family:Arial,sans-serif;max-width:900px;margin:auto'>
    <h2 style='color:#1a73e8'>🚀 InternHunter Daily Digest — {datetime.now().strftime('%d %b %Y')}</h2>
    <p>Found <b>{len(opportunities)}</b> new internship opportunities today.</p>
    <table style='border-collapse:collapse;width:100%'>
        <tr style='background:#1a73e8;color:white'>
            <th style='padding:8px'>Title</th><th>Role</th><th>Stipend</th>
            <th>Deadline</th><th>Location</th><th>Apply</th>
        </tr>
        {rows}
    </table>
    <br><p style='color:grey;font-size:12px'>InternHunter Bot · auto-generated</p>
    </body></html>"""
