import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/outputs/aqone_profitable_case/AqOne_Startup_Financing_Exercises_Profitable_Case.xlsx";
const outputDir = "C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/outputs/aqone_company_case";
const outputPath = `${outputDir}/AqOne_Startup_Financing_Exercises_Company_Case.xlsx`;

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const income = workbook.worksheets.getItem("iS");
const bep = workbook.worksheets.getItem("BEP");
const preOp = workbook.worksheets.getItem("pre-operating");

income.getRange("D19:D20").values = [[36000], [24000]];
income.getRange("D21:D22").values = [[24000], [6000]];
income.getRange("D24:D25").values = [[60000], [12000]];
income.getRange("D27:D30").values = [[15000], [12000], [20000], [18000]];
income.getRange("D32:D34").values = [[30000], [40000], [24000]];
income.getRange("D37").values = [[15000]];

bep.getRange("B9:B12").values = [[671000], [60000], [30000], [25000]];

preOp.getRange("D11:D28").values = [
  [15000], [3000], [2000], [2000], [500], [10000], [5000], [1000],
  [4166.6666667], [1250], [1000], [1666.6666667], [1500], [6250],
  [2500], [3333.3333333], [2000], [1250],
];
preOp.getRange("F10").formulas = [["=SUM(D11:D28)"]];
preOp.getRange("F31").formulas = [["=F10*12"]];

workbook.recalculate();

const values = {
  revenue: income.getRange("E7").values[0][0],
  cogs: income.getRange("E15").values[0][0],
  grossProfit: income.getRange("E16").values[0][0],
  operatingExpenses: income.getRange("E37").values[0][0],
  netProfit: income.getRange("E38").values[0][0],
  netMargin: income.getRange("G38").values[0][0],
  breakEvenPrice: bep.getRange("B30").values[0][0],
  breakEvenUnits: bep.getRange("E16").values[0][0],
  preOpMonthly: preOp.getRange("F10").values[0][0],
  preOpAnnual: preOp.getRange("F31").values[0][0],
  capitalAsk: preOp.getRange("F29").values[0][0],
  endingCash: workbook.worksheets.getItem("CF").getRange("C32").values[0][0],
};

if (values.operatingExpenses !== 786000 || values.netProfit !== 109000) {
  throw new Error(`Unexpected company-case results: ${JSON.stringify(values)}`);
}

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
if ((formulaErrors?.matches ?? []).length > 0) {
  throw new Error(`Formula errors found: ${JSON.stringify(formulaErrors)}`);
}

await fs.mkdir(outputDir, { recursive: true });
for (const sheetName of ["iS", "BEP", "CF", "pre-operating"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/${sheetName.replace(/[^a-z0-9]+/gi, "_")}.png`, new Uint8Array(await preview.arrayBuffer()));
}

await (await SpreadsheetFile.exportXlsx(workbook)).save(outputPath);
console.log(JSON.stringify({ outputPath, values }, null, 2));
