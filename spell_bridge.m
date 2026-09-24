#import <Cocoa/Cocoa.h>
#include <string.h>

typedef struct {
    long location;
    long length;
    char word[256];
    char best_guess[256];
    int guess_count;
} SpellFinding;

int check_text_de(const char *utf8_text, SpellFinding *out_findings, int max_findings) {
    if (!utf8_text || !out_findings || max_findings <= 0) return 0;
    
    @autoreleasepool {
        NSSpellChecker *sc = [NSSpellChecker sharedSpellChecker];
        [sc setLanguage:@"de_DE"];
        
        NSString *text = [NSString stringWithUTF8String:utf8_text];
        if (!text) return 0;
        
        int count = 0;
        NSRange searchRange = NSMakeRange(0, [text length]);
        
        while (searchRange.location < [text length] && count < max_findings) {
            NSRange misspelledRange = [sc checkSpellingOfString:text startingAt:searchRange.location language:@"de_DE" wrap:NO inSpellDocumentWithTag:0 wordCount:NULL];
            if (misspelledRange.location == NSNotFound) break;
            
            NSString *word = [text substringWithRange:misspelledRange];
            NSArray *guesses = [sc guessesForWordRange:misspelledRange inString:text language:@"de_DE" inSpellDocumentWithTag:0];
            
            out_findings[count].location = misspelledRange.location;
            out_findings[count].length = misspelledRange.length;
            strncpy(out_findings[count].word, [word UTF8String] ?: "", 255);
            out_findings[count].word[255] = '\0';
            
            if (guesses && [guesses count] > 0) {
                out_findings[count].guess_count = (int)[guesses count];
                const char *first = [[guesses objectAtIndex:0] UTF8String];
                strncpy(out_findings[count].best_guess, first ?: "", 255);
                out_findings[count].best_guess[255] = '\0';
            } else {
                out_findings[count].guess_count = 0;
                out_findings[count].best_guess[0] = '\0';
            }
            
            count++;
            searchRange.location = misspelledRange.location + misspelledRange.length;
        }
        return count;
    }
}

int is_valid_word_de(const char *utf8_word) {
    if (!utf8_word || !*utf8_word) return 1;
    @autoreleasepool {
        NSSpellChecker *sc = [NSSpellChecker sharedSpellChecker];
        [sc setLanguage:@"de_DE"];
        NSString *wordStr = [NSString stringWithUTF8String:utf8_word];
        if (!wordStr) return 1;
        NSRange range = [sc checkSpellingOfString:wordStr startingAt:0 language:@"de_DE" wrap:NO inSpellDocumentWithTag:0 wordCount:NULL];
        return (range.location == NSNotFound) ? 1 : 0;
    }
}
