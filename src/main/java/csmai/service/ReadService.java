package csmai.service;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import csmai.model.OcrResult;

@Service
public class ReadService {

	@Value("${ocr.scripts.python.cmnd}")
	String pythonCmnd;
	
	@Value("${ocr.scripts.python.temporary}")
	String pythonTempDir;
	
	public OcrResult read(String path) {
		OcrResult rs = new OcrResult();
		Path filePath = Paths.get(path);
		String filename = filePath.getFileName().toString();
		try {
			String[] command = {"python", pythonCmnd + "demo/main.py", path, pythonTempDir + filename + ".txt"};
			System.out.println(pythonCmnd + "demo/main.py");
			System.out.println(path);
			System.out.println(pythonTempDir + filename + ".txt");
            ProcessBuilder builder = new ProcessBuilder(command);
            Map<String, String> env = builder.environment();
            // set environment variable u
            env.put("PYTHONPATH", pythonCmnd);
            Process pr = builder.start();
            BufferedReader reader = new BufferedReader(new InputStreamReader(pr.getInputStream()));
            String line;
            while((line = reader.readLine()) != null) {
            	System.out.println(line);
            }
            
            if (pr.waitFor() == 0) {
            	rs.result = "Error";
            	System.out.println("Run sucess");
            } else {
            	rs.result = "Error";
            	System.out.println("Run fail");
            }
            
    		InputStream fis = new FileInputStream(pythonTempDir + filename + ".txt");
    		InputStreamReader isr = new InputStreamReader(fis, Charset.forName("UTF-8"));
    		BufferedReader br = new BufferedReader(isr);
    		StringBuilder sb = new StringBuilder();
    		while ((line = br.readLine()) != null) {
    			sb.append(line);
    			sb.append(System.getProperty("line.separator"));
    		}
    		rs.result = sb.toString();
    		
		} catch (InterruptedException | IOException e) {
			e.printStackTrace();
			rs.result = "Error";
		}
		

		
		return rs;
	}
}
