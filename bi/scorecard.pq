// Create a text parameter ReportDirectory containing the local results folder.
let
    Source = Csv.Document(File.Contents(ReportDirectory & "/scorecard.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    BlankScores = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"score_pct"}),
    Typed = Table.TransformColumnTypes(BlankScores,
        {{"survey_year", Int64.Type}, {"entity_code", type text}, {"metric_code", type text},
         {"score_pct", type number}, {"entity_kind", type text}, {"missing_reason", type text}}, "en-US")
in
    Typed
