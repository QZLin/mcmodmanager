param(
    $generated_file = "guiapp.py",
    $target_file = "ModManagerGui.py",
    $win_merge = "C:\Programs\WinMerge\WinMergeU.exe"
)

Push-Location $PSScriptRoot

$start_head1 = '# build ui'
$end_head1 = 'def run(self):'

$start_head2 = '# build ui'
$end_head2 = '# END AUTOGENERATED CODE'

$source = Get-Content $generated_file -Raw
$target = Get-Content $target_file -Raw

$s1 = $source.IndexOf($start_head1)
$code_a = $source.Substring($s1, $source.IndexOf($end_head1) - $s1)

$s2 = $target.IndexOf($start_head2)

$code_b = $target.Substring($s2, $target.IndexOf($end_head2) - $s2)


$f1 = ($env:TEMP + "/" + (New-Guid))
$code_a > $f1
$f2 = ($env:TEMP + "/" + (New-Guid))
$code_b > $f2

Pop-Location