eval 'exec perl -S -s $0 ${1+"$@"}'
                    if $running_under_some_shell;

# $Id$

# We are reading the first tune:
$first_tune = 1;
$a_tune_has_been_found = 0;
$global_P_header = "";
$output_buffer = "";


if ($#ARGV == -1) {
    # No argument: use STDIN:
    abccat(STDIN);
}
else {
    # Deal with each given file:
    foreach $f (@ARGV) {
	open (INPUT, $f) or die "Cannot open abc file \"$f\"\n";
	abccat(INPUT);
    }
}
print "X:1\n";
if (defined $abccat_P_header) {
    print "P:$abccat_P_header\n";
    print "%%text instead of P:$global_P_header\n";
}
else {
    print "P:$global_P_header\n";
}
print $output_buffer;


# The abccat procedure.
# Take as input the file handle of the file to read.
sub abccat($) {
    my ($FILE) = @_;
    $line = "";
  LINE: while (<$FILE>) {
      # Discard the end of line character:
      chomp;
      # Add the current line to the line buffer:
      $line .= $_;

      if ($line =~ /^\s*([A-Z]):(.*)/) {
	  # This is a header line.
	  $header = $1;
	  $content = $2;
	  if ($line =~ /\\$/) {
	      # This is a continuation line: grab once more...
	      $line .= "\n";
	      next LINE;
	  }
	  deal_with_header($header, $content);
      }
      elsif ($line =~ /^%%abccat\sP:(.*)$/) {
	  print STDERR "Define an explicit global P:$1\n";
	  $abccat_P_header = $1;
      }
      elsif ($line =~ /^\s*$/) {
	  #print "Blank line!\n";
      }
      else {
	  output("$line\n");
      }
    $line = "";
  }
}


# Deal with the various headers.
# Take as input the header character and its value:
sub deal_with_header($$) {
    my ($header, $content) = @_;

    if ($header eq "X") {
	# The begin of a tune.
	$P_header_found = 0;
	if ($first_tune == 1 && $a_tune_has_been_found == 1) {
	    # Well, this is no longer the first tune:
	    $first_tune = 0;
	}
	$a_tune_has_been_found = 1;
	# Just display it:
 	output_header_as_text($header, $content);
   }
    elsif ($header eq "P") {
	if ($P_header_found == 0) {
	    # First P: of the tune. Remember the way to play:
	    $global_P_header .= $content;
	    # Ok, we've found the first P:
	    $P_header_found = 1;
	    # Just display it:
	    output_header_as_text($header, $content);
	}
	else {
	    # Just a part name:
	    output_header($header, $content);
	}  
    }
    elsif ("ABCDGHNORSZT" =~ /$header/) {
	# These commands can only appear once in the header.
	# Just output them as text since we cannot compute a global value ...
	output_header_as_text($header, $content);
    }
    else {
	output_header($header, $content);
    }  
}


# Output a header line.
# Take as input the header character and its value:
sub output_header($$) {
    my ($header, $content) = @_;
    
    output("$header:$content\n");
}


# Output a string.
sub output($) {
    my ($string) = @_;
    
    $output_buffer .= $string;
}


# Output a header line but as a text line.
# Take as input the header character and its value:
sub output_header_as_text($$) {
    my ($header, $content) = @_;
    
    output_as_text("$header:$content\n");
}


# Output a string as a text line.
sub output_as_text($) {
    my ($string) = @_;
    
    output("%%text $string");
}
