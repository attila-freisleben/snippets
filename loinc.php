<?php

/*
REST endpoint to generate a valid value for a LOINC code: https://loinc.org/

Helper for realistic data generation in FHIR format: http://fhir.org/

Returns a LOINC code with random generated valid values in FHIR format
When id is set then for specific id, 
when random & class is set then a random code from specific class 
*/

set_time_limit(180);
error_reporting(E_ERROR);
set_include_path(".:/data/www/xfhir/inc");
include_once("include.php");

function return_data($result){
    header("Content-Type: application/fhir+json",true,$result['status']);
    echo  json_encode($result['body'],JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
 }

$debug = $_REQUEST['_debug']!="";

$random = $_REQUEST['random'];
$class = $_REQUEST['class'];
$system = $_REQUEST['system'];
$withrange = $_REQUEST['withrange'];
$id = $_REQUEST['id'];

if(!isset($id) && !isset($class) && !isset($random) ){
 echo "xfhir.net Loinc endpoint"; exit;
}

logger("$method\t".$resource."\t".urldecode($_SERVER['REQUEST_URI']));

$db= new db_connect($dbparams);
$db2= new db_connect($dbparams);

/*** get request body */
$jdoc    = file_get_contents('php://input');
if($jdoc!="")
{
  $jsonarr = json_decode(utf8_encode($jdoc),true);
  /*** check JSON syntax */
  if(json_last_error()!==JSON_ERROR_NONE)
  {
    $result[0]['status'] = '400';
    $result[0]['body'] = json_encode(array(utf8_encode("JSON error: ".json_last_error_msg())));
    return_data($result);
    exit();
  }
}

/*** process request params: put relevant FHIR fields into $_vars  */
$q = explode('?',urldecode($_SERVER['REQUEST_URI']));
$q = explode('&',$q[1]);

foreach($q as $line)
{
 $p = explode('=',$line);
 if($p[0]!="")
   $_vars[$p[0]][] = $p[1]; 
}


/*********************** getByID **********************************/
if(isset($id)){
 $db->db_exec("select a.*,b.name as classname from LOINC.Loinc  a join LOINC.Classes b on (a.classtype=b.type) where loinc_num='$id'");
 $rs = $db->db_fetch();
}

/******************get a random value from a class***********************************/
if(isset($random)){
 if(isset($class)){
  $db->db_exec("select * from LOINC.Classes where name='$class'");
  $rs = $db->db_fetch();
  
  if(!isset($rs)){
    $db->db_exec("select * from LOINC.Classes ");
    for(;$rs = $db->db_fetch();)
       $classes .= $rs['NAME'].",";
    $result['status'] = '404';
    $result['body'] = "Class $class not found. Valid classes are ".substr($classes,0,-1);  
    return_data($result);
    exit() 
  }
 }	
 /******************construct SQL ***********************************/
 $classcond = isset($rs['TYPE']) ? " classtype='".$rs['TYPE']."' " : "";
 $syscond   = isset($system) ? "  a.system='$system' " : "";
 $rangecond = isset($withrange) ? "  a.unitsandrange like '%:%' " : "";

 $where = $classcond.$syscond.$rangecond!="" ? "where  " : "";
 $and   = $classcond!="" && $syscond!="" ? "and" : "";
 $and2  = $syscond=="" && $rangecond!="" ? "and" : "";

 $db->db_exec("select count(*) as db from (select a.*,b.name as classname from LOINC.Loinc a join LOINC.Classes b on (a.classtype=b.type) $where $classcond $and $syscond $and2 $rangecond) a");
 $rs = $db->db_fetch();
 $rand = round(rand(0,$rs['DB']),0);

 $db->db_exec("select a.*,b.name as classname  from LOINC.Loinc a join LOINC.Classes b on (a.classtype=b.type) $where $classcond $and $syscond $and2 $rangecond limit $rand,1");
 $rs = $db->db_fetch();

}
 
 if(isset($rs)){

   $ez = array("[","(",")","]");
   foreach($ez as $as)
     $er[] = "";      
   
   $ret['coding']['code']    = $rs['LOINC_NUM'];
   $ret['coding']['system']  = "http://loinc.org";
   $ret['coding']['display'] = $rs['LONG_COMMON_NAME'];

   $ret['LOINC']['Class']    = $rs['CLASSNAME'];
   $ret['LOINC']['System']   = $rs['SYSTEM'];
   $ret['LOINC']['ShortName']    = $rs['SHORTNAME'];

   if($rs['UNITSANDRANGE']!=""){
   	
   $uars = explode(";",substr($rs['UNITSANDRANGE'],0,-1));
   foreach($uars as $uar){
     $w = explode(":",$uar);
     $unit = $w[0];
     if(isset($w[1])){ 
        $range = explode(",",str_replace($ez,$er,$w[1])); 
        $min  = isset($range[0]) ? $range[0] : "";
        $max  = isset($range[1]) ? $range[1] : "";
        $uararr[$unit] = array("min"=>$min,"max"=>$max);
        if(isset($uararr))
           $refrange[$unit] = array("low"=>$min,"high"=>$max);
       }
    }    
   } //isset uarrarr
    else
     $uararr= $rs['EXAMPLE_UCUM_UNITS']!="" ? array($rs['EXAMPLE_UCUM_UNITS']=>array("min"=>"","max"=>"")) :"" ;


     if(is_array($uararr) || $uararr!="")
       $ret['LOINC']['UnitsAndRange']      = $uararr;
     if($rs['EXAMPLE_UCUM_UNITS']!="")
       $ret['LOINC']['example_ucum_units'] = $rs['EXAMPLE_UCUM_UNITS'];

     if($rs['EXAMPLE_UCUM_UNITS']!=""){
        $ret['UCUM'] = array("unit"=>$rs['EXAMPLE_UCUM_UNITS'],'system'=>"http://unitsofmeasure.org","code"=>$rs['EXAMPLE_UCUM_UNITS']);
    }  

    if(isset($refrange))
       $ret['referenceRange'] = $refrange;

    $result['status'] = '200';
    $result['body'] = $ret;
  }
 else{  //$rs not set
   $result['status'] = '404';
   $result['body'] = "LOINC code:$id not found";
 }

return_data($result);

$db2->db_close();
$db->db_close();
 


?>
