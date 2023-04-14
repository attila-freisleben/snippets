/*
Generates a PDF doc from a specific table for a given term
*/

CREATE OR REPLACE FUNCTION FEKVO.VIG_TVK(P_IDOSZAK VARCHAR2 )
   RETURN BLOB
AS
   REBLOB   BLOB;
   P_SEL    VARCHAR2 ( 32000 );
BEGIN
   P_SEL :='
   select decode(grouping(a.terkat),1,''Összesen'', a.terkat) as terkat,
      a.partner_id as id,
      b.name,
      sum(tvk) as tvk,
      sum(ath_marv) as ath_marv,
      sum(havi_marv) as havi_marv,
      sum(gongy_marv) as gongy_marv
   from fek_tvk a join partner b on (a.partner_id=b.id)
   where a.idoszak=''' || P_IDOSZAK || ''' 
   group by rollup(a.terkat,(a.partner_id,b.name))';

   P04_FIN_KOZOS.PDFDOC.INIT('L');
   P04_FIN_KOZOS.PDFDOC.CIM('TVK visszaigazoló' );
   P04_FIN_KOZOS.PDFDOC.TABLAZAT(P_SEL);
   REBLOB := P04_FIN_KOZOS.PDFDOC.MAKE();
RETURN REBLOB;
END;
/
