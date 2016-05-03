#!/usr/bin/perl
use MIDI;
use File::Basename qw(basename);
use strict;
use CGI;
use CGI::Carp qw(warningsToBrowser fatalsToBrowser);
my $q = CGI->new;
my $in = $q->upload("son");
    print $q->header,
    $q->start_html('SON 2 MIDI'); # start the HTML
if (!$in) {
    print $q->h1('Upload SON file'),         # level 1 header
    $q->start_multipart_form(),
    $q->filefield(-name => "son"),
    $q->submit, $q->end_form, $q->end_html;
exit;
}
my $fname = $q->param("son");
$fname =~ s/\..*?$/.mid/;
my $output = "tmp/midis/".basename($fname);
print $q->h1("Results");
$| = 1;
print "<pre>";
seek $in, 0x5ac8, 0;
local$/;
my @lines = split /(?:\x7f\xff\xff\xff)|(?:\x00\x0f\xff\xff)/, scalar <$in>;
my @tracks;
while (my $track = shift @lines) {
    my $stuff = {};
    $stuff->{header} = substr($track, 0, 24,"");
    $track =~ s/^(.{8})//; $stuff->{title} = $1; 
    $stuff->{data} = $track;
    push @tracks, $stuff;
}

sub tick2time {
    my $ticks = shift;
    my $bar = int($ticks / 768);
    $ticks %= 768;
    my $beat = int($ticks / 192);
    $ticks %= 192;
    "$bar/$beat/$ticks";
}

sub data2event { 
    my $data = shift;
    my $line = shift;
    my ($note, $status, $pos1, $pos2, $vel, $arg3) = map ord, split//, $line;
    if ($status =~ /(14[45])/) {
        $pos1 += 256 *($1-144);
        $status = "note_on";
        $vel = $vel - 2;
        if ($vel <0) { $status="note_off" }
        $vel = abs $vel;
        my $pos = $pos1*256 +$pos2;
        my $delta = $pos - $data->{counter};
        #$delta -= 4608 if $data->{counter} == 0;
        (print "Negative delta $delta! (We are at $pos, were at
        $data->{counter})"), return if $delta < 0;
        $data->{counter} = $pos;
        return [ $status, $delta, $data->{channel}, $note, $vel ]
    } elsif ($status == 224) {
        my $pitch = ($vel -129)*(8192/128);
        my $pos = $pos1*256 +$pos2;
        my $delta = $pos - $data->{counter};
        $data->{counter} = $pos;
        return [ "pitch_wheel_change", $delta, $data->{channel}, $pitch ]
    }
    print "Skipping over unknown event $status ($note, $vel, $arg3) at position ".tick2time($pos1*256+$pos2);
    return;
}

my $channel = 0;
my @out;
for (@tracks) {
   my $size = 6;
   $_->{data} =~ s/.{14}//; my $x=$1;
   next if length($_->{data}) == 0;
   print $_->{title}.": ".length($_->{data});
   print " (".(length($_->{data})/$size).")\n";
   if ($_->{title} =~ /drum|ercuss/i) { $channel = 10 } else { $channel++ }

   $_->{counter} = 0;
   $_->{channel} = $channel;
   $_->{events} = [ 
    [track_name => 0 => $_->{title} ],
   ];
   while (my $foo = substr($_->{data}, 0, $size, "")) {
       push @{$_->{events}}, data2event($_, $foo);
   }
   my $track = MIDI::Track->new;
   $track->events(@{$_->{events}});
   push @out, $track;
}

my $song = MIDI::Opus->new(
{ 'format' => 1, 'ticks' => 192, 'tracks' => [ @out ] } );
 
print "Writing on $output";
print "</pre>";
$song->write_to_file($output);
print "<hr>You may download your file <a href=\"$output\">here</a>.";
