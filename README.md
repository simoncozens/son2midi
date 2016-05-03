<head>
<meta http-equiv="Content-Type" content="text/html; charset=US-ASCII">
<title>October, 2004: Musical Archaeology With Perl</title>
</head><!--Copyright &#169; The Perl Journal-->
# Musical Archaeology With Perl

_The Perl Journal_ October, 2004

## 

### By Simon Cozens
_Simon is a freelance programmer and author, whose titles include Beginning Perl (Wrox Press, 2000) and Extending and Embedding Perl (Manning Publications, 2002). He's the creator of over 30 CPAN modules and a former Parrot pumpking. Simon can be reached at simon@ simon-cozens.org._
* * *

I've recently moved house, and one of the joys of moving house is that you occasionally turn up things you'd forgotten existed. One of the most bittersweet things I turned up was a backup CD of my computer from about 1998. The sense of morbid curiosity was overpowering, and after wading through the pictures of ex-girlfriends, university-era essays, and curious Windows applications, I found a directory that was itself a backup of another computer. From 1994.

At the time I was in high school, and was a very profilic music composer. Looking at the titles of the song files and remembering the songs I wrote at the time, I realized that one or two of them weren't all that bad, and I'd quite like to listen to them again. This is when I remembered that I didn't use real computers in 1994. The files came from an Atari ST and were written by a program called Notator SL.

Searching the Web, the only two ways I could find to use these files again were either to find an Atari ST already running Notator, or buy a copy of Notator's grandchild, Logic (formerly from eMagic, now owned by Apple). Logic is expensive, and the chances of finding anyone in my neighborhood with a 10-year-old music computer set-up were pretty slim.

When something like this happens, it takes me over. I have to find a solution. Besides, it's more fun than packing. There was only one thing for it: I was going to have to decode the file format myself.

### Laying the Foundations

Since I had a lot of these .SON files, the first step was to take a couple of them, and discover how they differed. Thankfully, I knew that I had a few files that were very similar in nonessential regardsthe drum mappings were the same, the track names and parameters were the same, and only the actual notes played were different. So I sat down with a hex editor and each of the files open in its own window, and wrote out what I saw (see [Figure 1](0410df1.html)).

For the time being, all I cared about was the data on each track. With the track name appearing in plain text, 8 bytes padded with spaces, I knew where the tracks began. Unfortunately, I couldn't work out where a given the track ended. I could see that "PIANO" was a track name and started a new track, but I couldn't make a rule for that to explain it a computer.

So I came at things from a different angle. I knew that the data was going to be something like MIDI dataa series of _n_-byte messages. So the first thing I needed to do was work out the value of _n_. We can do this by spotting patterns. I wrote something quick to dump the output in rows of _n_ bytes:

> open IN, shift or die $!;
> seek IN, 0x5ae0, 0;
> my $track;
> read(IN, $track, 8) and print "Track name: '$track'\n";
> my $n = 3;
> my $data;
> while (read(IN, $data, $n)) {
> my @bytes = map ord, split //, $data;
> print join " ", map { sprintf "%x", $_ } @bytes;
> print "\n";
> }

We loop over the file, reading in _$n_ bytes at a time into _$data_. Then these are split into their individual bytes_split //_ splits every single character into a separate array element. We convert them to their ASCII code, turn that into hex, and then dump them out.

I started with _$n_ = 3 because a lot of MIDI commands are 3 bytes, and that seemed like a good guess. I then ran it on the shortest file I could find, and got this:

> Track name: '*Undo* '
> 0 0 9c
> 22 20 59
> 58 0 80
> 21 0 0
> 2 23 2d
> 90 21 0
> 81 0 39
> 90 21 0
> 81 0 3d
> 90 21 0
> 81 0 40
> 90 21 0

Not bad. We have a few rows that I guessed were to do with setting up, then we settle into a pattern of 90 21 0 and then 81 0 3x. These could be something to do with notes, I guess. But the way that they alternate like that, maybe the two rows are part of the same event. We set _$n = 6_, and we see:

> Track name: '*Undo* '
> 0 0 9c 22 20 59
> 58 0 80 21 0 0
> 2 23 2d 90 21 0
> 81 0 39 90 21 0
> 81 0 3d 90 21 0
> 81 0 40 90 21 0
> 81 0 2d 90 23 ff
> 1 0 39 90 23 ff
> 1 0 3d 90 23 ff
> 1 0 40 90 23 ff
> 1 0 31 90 24 0

Oh, now this is a bit more interesting. We notice that the last 2 bytes form a number that is monotonically increasing. What could monotonically increase over events in a track? Maybe that's the time that the event occurs. The fourth column is almost always 90; maybe that signifies that this is a note.

There's a way to checkwe run it on a file with a drum part as the first track, and, given that I vaguely remember what the song sounds like, I can work out the interval between drum beats. That will tell us how to convert between 21 0 and some measure-beat-tick value (or bar-beat-tick, since I'm from the UK and we use different terminology over here). Here's a bit of the dump of a drum track:

> 01 00 24 90 36 00
> 81 00 2e 90 36 00
> 81 00 36 90 36 00
> 81 00 24 90 36 5f
> 01 00 2e 90 36 5f
> 01 00 36 90 36 5f
> 01 00 36 90 36 60
> 81 00 36 90 36 bf
> 01 00 26 90 36 c0
> 81 00 2e 90 36 c0
> 81 00 36 90 36 c0

Now we only see two values for the first row: 81 and 01. We'll assume that these are somehow paired, so we'll only look at the 81 events for now. We'll also only concentrate on unique values of the last two columns, and we get a sequence like this:

> 36 00 / 36 5f / 36 bf / 36 c0 / 37 1f / 37 7f 
> 37 80 / 37 df / 38 3f / 38 40 / 38 9f / 38 ff
> 39 00 / 39 5f / 39 bf / 39 c0 / 3a 1f / 3a 7f 
> 3a 80 ...

I happen to know that there's a tambourine hit every quaver (that's English for an eighth-note) in this drum track, and there's an increment of 0x5f (96) between every note. That's when it all came back to meNotator uses 768 ticks in a measure. An eighth of 768 is 96. So if we take these 2 bytes as representing a 2-byte integer, we can convert them to musical time, like so:

> ub tick2time {
> my ($hi, $lo) = @_;
> my $ticks = (256*$hi) + $lo;
> my $bar = int($ticks / 768);
> $ticks %= 768;
> my $beat = int($ticks / 192);
> $ticks %= 192;
> "$bar/$beat/$ticks";
> }

Now we can improve our dumping tool a little:

> while (read(IN, $data, $n)) {
> my @bytes = map ord, split //, $data;
> print join " ", map { sprintf "%02x", $_ } @bytes[0..3];
> print " [".tick2time(@bytes[4..5])."]";
> print "\n";
> }

This gives us the beginning of a drums track, like so:

> 00 00 9c 22 [10/2/152]
> 18 00 80 a1 [0/0/0]
> 02 23 2e 90 [12/3/96]
> 81 00 2e 90 [12/3/191]
> 01 00 24 90 [13/0/0]
> 81 00 2e 90 [13/0/0]
> 81 00 31 90 [13/0/0]
> 81 00 36 90 [13/0/0]
> 81 00 24 90 [13/0/95]
> 01 00 2e 90 [13/0/95]
> 01 00 31 90 [13/0/95]

From this we can tell that the first two lines really aren't related, and that the song appears to start 10 measures in. We'll ignore the latter detail for now, since it's just cosmeticwe can shift all the tracks back to the start in a more sophisticated sequencerand concentrate on those two lines of set-up data. The beginning of the third line starts to look a little suspect too: Every other line starts 81 00 or 01 00.

Perhaps what's actually going on is that the data starts at 2e 90, and we have not 12 but 14 bytes of setup. Then we have one number that fluctuates a bit; 90 for a note, the time, then some other numbers.

This requires some major changes to our dumper script:

> read(IN, $track, 8) and print "Track name: '$track'\n";
> my $setup;
> read(IN, $setup, 14); 
> while (read(IN, $data, $n)) {
> my @bytes = map ord, split //, $data;
> print join " ", map { sprintf "%02x", $_ } @bytes[0..1];
> print " [".tick2time(@bytes[2..3])."] ";
> print join " ", map { sprintf "%02x", $_ } @bytes[4..5];
> print "\n";
> }

And we now see:

> Track name: 'Drums '
> 2e 90 [12/3/96] 81 00
> 2e 90 [12/3/191] 01 00
> 24 90 [13/0/0] 81 00
> 2e 90 [13/0/0] 81 00
> 31 90 [13/0/0] 81 00
> 36 90 [13/0/0] 81 00
> 24 90 [13/0/95] 01 00
> 2e 90 [13/0/95] 01 00
> 31 90 [13/0/95] 01 00
> 36 90 [13/0/95] 01 00

Ah, now this is looking promising. But now what? This is the curse of reverse engineeringyou solve one piece of the problem, but then you're back to square one for the other pieces until inspiration strikes again.

### MIDI Inspiration

Inspiration struck again while I was reading Sean Burke's MIDI-Perl documentation. I figured I needed to translate these files into MIDI files to do anything with them, so I took a look at how to produce MIDI files. I learned two things therefirst, MIDI files don't encode note length, but have paired "note on" and "note off" events. Maybe that's our paired 81 and 01 events.

Second, the MIDI Perl module exports a number of hashes, including _%number2note_ and _%notenum2percussion_, which turn a MIDI file's representation of a pitch or percussion instrument name into an English representation. Maybe even if Notator didn't exactly store its events in MIDI file format, it at least used the same representation for pitch. So we take the first column of our dump, the one that bobbles about a bit, and feed it through one of these hashes:

> my @bytes = map ord, split //, $data;
> print $track =~ /drum|percuss/i ?
> $MIDI::notenum2percussion{$bytes[0]} :
> $MIDI::number2note{$bytes[0]};
> print join " ", map { sprintf "%02x", $_ } $bytes[1];
> print " [".tick2time(@bytes[2..3])."] ";
> print join " ", map { sprintf "%02x", $_ } @bytes[4..5];
> print "\n";

This turns our drum track into:

> Bass Drum 1 90 [17/2/0] 81 00
> Open Hi-Hat 90 [17/2/0] 81 00
> Tambourine 90 [17/2/0] 81 00
> Bass Drum 1 90 [17/2/95] 01 00
> Open Hi-Hat 90 [17/2/95] 01 00
> Tambourine 90 [17/2/95] 01 00
> Bass Drum 1 90 [17/2/96] 81 00
> Tambourine 90 [17/2/96] 81 00
> Bass Drum 1 90 [17/2/191] 01 00
> Tambourine 90 [17/2/191] 01 00

This looks good enough, and we can check to see if an ordinary music track is more or less in key:

> Track name: 'Vocals '
> E5 90 [10/3/144] 81 00
> E5 90 [10/3/191] 01 00
> Gs5 90 [11/0/0] 81 00
> Gs5 90 [11/0/47] 01 00
> Gs5 90 [11/0/48] 81 00
> Gs5 90 [11/0/191] 01 00
> Fs5 90 [11/1/0] 81 00
> Fs5 90 [11/1/95] 01 00
> E5 90 [11/1/96] 81 00
> B5 90 [11/1/144] 81 00
> E5 90 [11/1/191] 01 00
> B5 90 [11/2/47] 01 00

This is consistent with a song in E major. Finally, I noticed that for some songs, as well as 81 and 01, there were note events with other values for this column; I guessed that this related to the velocity of the note, another MIDI concept. Velocity represents conceptually how hard the note is struck; it's a bit like volume, but can also change the timbre of the tone. For now, though, we'll take numbers more than 0x80 to mean note on with full velocity, and less than 0x80 to mean note off.

We have everything we need to convert a single track into MIDI formatexcept we still don't know how a track ends. Our notes say that it ends with some number of 0 bytes, but we don't know how many. It was back to the hex editor.

After comparing files and tracks in the hex editor once again, I came up with an ideawhat if the track name wasn't the first bit of data in the track? What if there was some other setup data before the name of each track? That section starting just before the tracks that I'd labeled as "DATA" might be part of the track header. This would mean that the stray null bytes I'd been seeing were not the end of the track, but the beginning.

This cracked itI found that each track began with either the 4 bytes 7f ff ff ff or 00 0f ff ff. Then there was a 24-byte header, followed by the track name, and the 14 other header bytes I had determined earlier. Now I could write the MIDI file translator.

### The Translator

First, I decided to read the data in with the Perl slurp operator and regular expressions, instead of the more cumbersome _read_. This allowed me to use _split_ to split up the tracks on the boundaries that I'd just discovered. I also decided to get the data together first, then pass over it, converting it to MIDI tracks. Here's the part that reads in the tracks:

> my ($input, $output) = @ARGV;
> open IN, $input or die $!;
>     
> seek IN, 0x5ac8, 0;
> local $/;
> my $boundary = qr/(?:\x7f\xff\xff\xff)|(?:\x00\x0f\xff\xff)/
> my @lines = split /$boundary/, scalar <IN>;
> my @tracks;
> for my $track (@lines) {
> my $stuff = {};
> $stuff->{header} = substr($track, 0, 24,"");
> $track =~ s/^(.{8})//; $stuff->{title} = $1;
> $stuff->{data} = $track;
> push @tracks, $stuff;
> }

Now we need to convert our Notator events to MIDI events. There are a couple of things we have to know about MIDI events first, however. First, although we have "absolute" times, in terms of measures, beats and ticks, MIDI files actually deal in terms of delta timethat is, an event is placed a number of ticks after the previous event. This means we need a counter to keep track of where we're up to in the track.

Next, whereas Notator deals in terms of tracks and events on a track, a MIDI file has both tracks and channels. We need to assign a channel to each track, and then spit out that channel number with each of the track's events. Finally, MIDI events are binary data, but the MIDI-Perl distribution makes it relatively easy to construct them by allowing us to specify them as an array of arrays. For instance, the first event we want to spit out is:

> [track_name => 0 => $track->{title}]

This puts the track name at time-position zero in the track. Note that events look like this:

> [note_on => $time, $track->{channel}, $note, $velocity]

We want to build up an array of these events, and then turn them into a _MIDI::Track_ object. Here's how we do it.

> my $channel = 0;
> my @midi;
> for my $track (@tracks) {
> $track->{data} =~ s/.{14}//; # Rest of header
> next if length($track->{data}) == 0;
> print $track->{title}. "\n";
>     
> $track->{counter} = 0;
> $track->{channel} = $channel++;
> $track->{events} = [
> [track_name => 0 => $track->{title}],
> ];
> my $size = 6;
> while (my $event = substr($track->{data}, 0, $size, "")) {
> push @{$track->{events}}, data2event($track, $event);
> }
> my $midi_track = MIDI::Track->new;
> $midi_track->events(@{$track->{events}});
> push @midi, $midi_track;
> }

Notice that we're treating _$track_ a little like an object, which stores all its own data inside the hash reference; it knows where we are in the song (_$track-\>{counter}_), the track's channel, the MIDI events, and so on. The only mystery is _data2event_, which turns the 6 bytes of data into an array reference representing a MIDI event:

> sub data2event { 
> my $track = shift;
> my $line = shift;
> my ($note, $status, $pos1, $pos2, $vel, $arg3) = 
> map ord, split//, $line;
> if ($status == 0x90) {
> $status = "note_on";
> $vel = $vel - 0x80;
> if ($vel <0) { $status = "note_off" }
> $vel = 127;
> my $pos = $pos1*256 +$pos2;
> my $delta = $pos - $track->{counter};
> $track->{counter} = $pos;
> return [$status, $delta, $track->{channel}, $note, $vel]
> } 
> warn "Skipping over unknown event $status ($note, $vel, $arg3)
> at position ".tick2time($pos1,$pos2);
> return;
> }

Notice that at present, we don't know what _$arg3_ is for. However, we do now know that if we see any events that aren't 0x90, then we get a warning. We'll come back to this in a moment. To finish off, we now have an array of _MIDI::Track_ objects.

Turning these into a MIDI file is now easy:

> $song = MIDI::Opus->new(
> { 'format' => 1, 'ticks' => 192, 'tracks' => \@midi } 
> );
>     
> warn "Writing on $output";
> $song->write_to_file($output);

This creates a MIDI format 1 file, with a rather arbitrary tempo, and fills it with our tracks.

I ran it on one of my old compositions, and out popped a working MIDI file. After a few minutes, fiddling around with instrumentation on a rather more modern sequencer, my 10-year-old music file was playing in all its glory.

### Later Improvements

Well, most of its glory. I got quite a few of those warnings telling me it had skipped over some events. Thankfully, it was now much, much easier to work out what those events should be.

So when the bass guitar was supposed to slide up and down but instead we got a load of warnings about an unknown event 224, we can guess that 224 means "pitch wheel." I used the original dumper and grepped for events with a code of 224, and found that the velocity moved around, centering on 128. MIDI files, on the other hand, encode pitch wheel changes not on a scale of 0 to 255 but a scale of -8192 to 8192, so I needed to do a bit of scaling. It was then easy enough to drop another stanza into _data2event_.

> elsif ($status == 224) {
> my $pitch = ($vel -129)*(8192/128);
> my $pos = $pos1*256 +$pos2;
> my $delta = $pos - $track->{counter};
> $track->{counter} = $pos;
> return ["pitch_wheel_change", $delta, $track->{channel}, $pitch]
> }

Now there was one final problem. Songs longer than 85 measures were getting truncated, and I was getting lots of warnings about event 145. I thought about this, and realized that the 2-byte position counter could only go up to 65535 ticks, and 65535 ticks was just over 85 measures. Then we flip over from a note being event 144 to being 145it seems that Notator used some bits in the "event type" byte to extend the position counter. This is pretty hateful, but I suppose it's better than restricting everyone to short songs. The conversion program had to change, like so:

> my ($note, $status, $pos1, $pos2, $vel, $arg3) = map ord, split//, $line;
> if ($status =~ /(14[45])/) {
> $pos1 += 256 *($1-144);

This still doesn't cover everything that can happen inside a Notator file, but at least it gets the notes out, and it's enough for me to play around with those old songs again. If, by some strange chance, you have a bunch of Notator songs and a sense of nostalgia, you can get my converter from http://simon-cozens.org/ programmer/releases/son2midi.pl. But bewarenext time you get stuck in the early nineties, Perl might not be able to drag you back...

**TPJ**

