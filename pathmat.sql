 /*
 Checking if condition is pathological maternity.
 Part of DRG classification.
 Oracle 12c, needed to hint extensively as optimizer was unable to cope with it reliably.
 */

SELECT /*+ dynamic_sampling(tfd 10)   index(tfd i_fdt_imitbtb) index(hdcs i_hdcs1) index(hd i_hdcsb) */
       DISTINCT
       tfd.idoszak,
       tfd.megye,
       tfd.intkod,
       '1.1.2 BNO CSOPORT - path. terh.',
       tfd.kulcs,
       hd.focsop,
       hd.alhbcs,
       (SELECT /*+ index(ha i_ha3) */
               DISTINCT ha.suly
          FROM hbcs_all ha
         WHERE     hd.hbcs = ha.hbcs
               AND tfd.fin_idoszak BETWEEN ha.ervtol
                                       AND NVL (ha.ervig, tfd.fin_idoszak)),
       NVL (hd.fcsop, '') || hd.bcsop,
       NVL (
           (SELECT diag
              FROM hbcs_maxtipus hmt
             WHERE     tfd.fin_idoszak BETWEEN hmt.ervtol
                                           AND NVL (hmt.ervig,
                                                    tfd.fin_idoszak)
                   AND hd.alhbcs = hmt.alhbcs
                   AND NVL (hd.tipcsop, 'x') = NVL (hmt.diag_tip, 'x')),
           (SELECT COUNT (DISTINCT bcsop)
              FROM hbcs_diag hd2
             WHERE     hd2.alhbcs = hd.alhbcs
                   AND tfd.fin_idoszak BETWEEN hd2.ervtol
                                           AND NVL (hd2.ervig,
                                                    tfd.fin_idoszak))),
       tfd.fin_idoszak,
       tfd.tsz,
       tfd.bnotip,
       tfd.esetid
  FROM tmp_fek_diag tfd, hbcs_diag hd, HBCS_DIAG_CSOPORT HDCS
 WHERE     tfd.idoszak = check_idoszak
       AND tfd.megye = p_megye
       AND tfd.intkod = p_intkod
       AND HD.BNO = HDCS.CSOPORT
       AND tfd.bno = HDCS.BNO
       AND hd.bno = ('14.A')
       AND tfd.fin_idoszak BETWEEN hd.ervtol
                               AND NVL (hd.ervig, tfd.fin_idoszak)
       AND tfd.fin_idoszak BETWEEN hdCS.ervtol
                               AND NVL (hdCS.ervig, tfd.fin_idoszak)
       AND hd.tipus LIKE '%' || tfd.bnotip || '%'
       AND NOT EXISTS
               (SELECT /*+ hash_aj index(hd2 i_hdtars2) */
                       alhbcs
                  FROM hbcs_diag hd2
                 WHERE     hd.alhbcs = hd2.alhbcs
                       AND hd2.tipcsop = 'SULYOS_TARSULT'
                       AND tfd.fin_idoszak BETWEEN hd2.ervtol
                                               AND NVL (hd2.ervig,
                                                        tfd.fin_idoszak))
       AND NOT EXISTS
               (SELECT /*+ hash_aj index(hd2 i_hdtars2) */
                       alhbcs
                  FROM hbcs_diag hd2
                 WHERE     hd.alhbcs = hd2.alhbcs
                       AND hd2.tipcsop = 'TARSULT'
                       AND tfd.fin_idoszak BETWEEN hd2.ervtol
                                               AND NVL (hd2.ervig,
                                                        tfd.fin_idoszak))
       AND (   EXISTS
                   (SELECT fe.esetid
                      FROM fek_elemi fe, fek_elemi fg
                     WHERE     tfd.esetid = fe.esetid
                           AND tfd.tsz = fe.tsz
                           AND fg.idoszak BETWEEN TO_CHAR (fe.felv_dat,
                                                           'YYYYMM')
                                              AND TO_CHAR (tfd.fin_idoszak,
                                                           'YYYYMM')
                           AND fe.megye = fg.megye
                           AND fe.intkod = fg.intkod
                           AND fe.tsz = fg.kistsz
                           AND fg.kistsz IS NOT NULL
                           AND fg.szul_dat - fe.felv_dat >= 12)
            OR EXISTS
                   (SELECT fe.esetid
                      FROM fek_elemi fe, fek_elemi fg
                     WHERE     tfd.esetid = fe.esetid
                           AND tfd.tsz = fe.tsz
                           AND fg.idoszak BETWEEN TO_CHAR (fe.felv_dat,
                                                           'YYYYMM')
                                              AND TO_CHAR (tfd.fin_idoszak,
                                                           'YYYYMM')
                           AND fe.megye = fg.megye
                           AND fe.intkod = fg.intkod
                           AND fe.kistsz = fg.tsz
                           AND fe.kistsz IS NOT NULL
                           AND fg.szul_dat - fe.felv_dat >= 12)
            OR EXISTS
                   (SELECT kulcs
                      FROM tmp_fek_mutet tfm, hbcs_beav hb
                     WHERE     tfd.esetid = tfm.esetid
                           AND tfm.mutkod = hb.who
                           AND tfd.fin_idoszak BETWEEN hb.ervtol
                                                   AND NVL (hb.ervig,
                                                            tfd.fin_idoszak)
                           AND tfd.tsz = tfm.tsz
                           AND   tfm.mut_dat
                               - (SELECT MIN (tfe.felv_dat)
                                    FROM tmp_fek_elemi tfe
                                   WHERE     tfe.esetid = tfd.esetid
                                         AND tfe.tsz = tfd.tsz) >=
                               12));
